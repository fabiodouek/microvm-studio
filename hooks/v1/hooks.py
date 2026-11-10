#!/usr/bin/env python3
# MicroVM Studio's lifecycle hook listener (Plan 9), installed in images whose recipe has hooks. The image's CMD
# starts it as root on 127.0.0.1, and the platform POSTs each hook to /aws/lambda-microvms/runtime/v1/<hook>:
#
# - ready (at build: every MicroVM is restored from the snapshot taken after it), suspend and terminate: 200.
# - run: once per MicroVM, before it's reported RUNNING. The body is {"microvmId": ..., "runHookPayload": "<JSON>"};
#   a payload of {"fileSystemId": "fs-...", "accessPointId": "fsap-..."} mounts that access point on /workspace the
#   way the app's connect-time root step does, under `timeout 45`. The outcome goes to the status file as one line,
#   `ok` or `failed <why>`, which the root step reads. Later run calls are ignored.
# - resume: checks the mount again (`stat -f` under a timeout), and mounts it afresh if it doesn't answer.
#
# Every hook answers 200, and within its timeout: one that fails or times out terminates the MicroVM. Work that takes
# longer goes on after the answer, and its outcome still reaches the status file. Mounts take the root step's lock,
# so the two never mount at once. Nothing secret passes through: the payload holds two IDs, and no body is logged.
#
# POSIX tools only (mountpoint, stat, timeout, umount, pkill, mount), and Python 3.9, as on Amazon Linux 2023.

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

FILE_SYSTEM_ID = re.compile(r"fs-[0-9a-f]{8,40}")
ACCESS_POINT_ID = re.compile(r"fsap-[0-9a-f]{8,40}")
MAX_BODY = 64 * 1024
HOOKS = ("ready", "run", "resume", "suspend", "terminate")
BAD_IDS = "the run payload's file system or access point ID isn't valid"


def log(message):
    # Never raises: a log that can't be written (a full root disk, a closed stderr) mustn't stop a hook answering.
    try:
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        sys.stderr.write("hooks: %s %s\n" % (stamp, message))
        sys.stderr.flush()
    except Exception:
        pass


def last_line(text, limit=200):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1][:limit] if lines else ""


def mount_target(body):
    """((file system ID, access point ID), None) from a run hook's body; (None, None) when it asks for no mount;
    (None, why) when its IDs aren't IDs."""
    try:
        request = json.loads(body.decode("utf-8")) if body.strip() else None
    except ValueError:
        return None, None
    payload = request.get("runHookPayload") if isinstance(request, dict) else None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload) if payload.strip() else None
        except ValueError:
            return None, None
    if not isinstance(payload, dict):
        return None, None
    file_system, access_point = payload.get("fileSystemId"), payload.get("accessPointId")
    if file_system is None and access_point is None:
        return None, None
    if not (isinstance(file_system, str) and FILE_SYSTEM_ID.fullmatch(file_system)
            and isinstance(access_point, str) and ACCESS_POINT_ID.fullmatch(access_point)):
        return None, BAD_IDS
    return (file_system, access_point), None


def alive(pid):
    if pid is None:
        return True   # its holder hasn't written it yet
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


class Mounter:
    def __init__(self, options):
        self.options = options
        self.work = threading.Lock()      # one mount at a time in here
        self.state = threading.Lock()
        self.writing = threading.Lock()
        self.ran = False
        self.target = None                # what the run hook mounted, for resume
        path = os.environ.get("PATH") or "/usr/bin:/bin"
        self.env = dict(os.environ, PATH=path + ":/usr/sbin:/sbin")

    # The hooks. Each returns the thread doing the work, if any, for the answer to wait on.

    def run_hook(self, body):
        with self.state:
            if self.ran:
                log("run: already done for this MicroVM; ignored")
                return None
            self.ran = True
        target, problem = mount_target(body)
        if problem:
            log("run: " + problem)
            self.write_status("failed " + problem)
            return None
        if target is None:
            log("run: nothing to mount")
            return None
        with self.state:
            self.target = target
        return self.start(target, "run")

    def resume_hook(self):
        with self.state:
            target = self.target
        return self.start(target, "resume") if target else None

    def start(self, target, hook):
        worker = threading.Thread(target=self.ensure, args=(target, hook), daemon=True)
        worker.start()
        return worker

    # Mounting.

    def ensure(self, target, hook):
        try:
            with self.work:
                self.write_status(self.mount(target, hook))
        except Exception as error:   # a hook must never fail
            log("%s: %r" % (hook, error))
            self.write_status("failed " + (last_line(str(error)) or "the hook listener hit an error"))

    def mount(self, target, hook):
        file_system, access_point = target
        point = self.options.mount_point
        if not self.take_lock():
            return "failed couldn't take the lock " + self.options.lock
        try:
            if self.healthy(point):
                log("%s: %s is mounted and answers" % (hook, point))
                return "ok"
            if shutil.which("mount.efs", path=self.env["PATH"]) is None:
                return "failed mount.efs isn't installed in this image"
            self.call(["umount", "-l", point], 20)
            self.call(["pkill", "-f", "efs-proxy.*" + file_system], 20)
            os.makedirs(point, exist_ok=True)
            limit = self.options.mount_timeout
            status, output = self.call(["timeout", str(limit), "mount", "-t", "efs", "-o",
                                        "tls,iam,accesspoint=" + access_point, file_system, point], limit + 15)
            if status == 0:
                log("%s: mounted %s" % (hook, point))
                return "ok"
            if status == 124:
                return "failed mounting %s took over %d seconds" % (point, limit)
            return "failed " + (last_line(output) or "mount exited with status %s" % status)
        finally:
            self.release_lock()

    def healthy(self, point):
        # mountpoint stats the directory too, which hangs on a dead mount, so both are timed.
        return (self.call(["timeout", "10", "mountpoint", "-q", point], 20)[0] == 0
                and self.call(["timeout", "10", "stat", "-f", point], 20)[0] == 0)

    def call(self, command, limit):
        try:
            done = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, env=self.env, timeout=limit)
            return done.returncode, done.stdout.decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            return 124, ""
        except OSError as error:
            return 127, str(error)

    # The root step's lock: a directory holding its holder's pid, taken over from a holder that's gone, or after
    # 120 seconds.

    def take_lock(self):
        lock = self.options.lock
        for waited in range(126):
            try:
                os.mkdir(lock, 0o700)
            except FileExistsError:
                if waited > 120 or not alive(self.holder(lock)):
                    shutil.rmtree(lock, ignore_errors=True)
                    continue
                time.sleep(1)
                continue
            except OSError as error:
                log("lock: %r" % error)
                return False
            with open(os.path.join(lock, "pid"), "w") as pid:
                pid.write("%d\n" % os.getpid())
            return True
        return False

    @staticmethod
    def holder(lock):
        try:
            with open(os.path.join(lock, "pid")) as pid:
                return int(pid.read().strip())
        except (OSError, ValueError):
            return None

    def release_lock(self):
        shutil.rmtree(self.options.lock, ignore_errors=True)

    def write_status(self, line):
        path = self.options.status
        line = " ".join(line.split("\n"))
        with self.writing:
            try:
                os.makedirs(os.path.dirname(path), mode=0o755, exist_ok=True)
                temporary = path + ".tmp"
                with open(temporary, "w") as status:
                    status.write(line + "\n")
                os.chmod(temporary, 0o644)
                os.replace(temporary, path)
                log("status: " + line)
            except OSError as error:
                log("status: couldn't write %s: %r" % (path, error))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "microvm-studio-hooks"

    def log_message(self, format, *args):
        pass   # the hook lines below say what happened, without bodies

    def read_body(self):
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            data = b""
            while True:
                size = int(self.rfile.readline(1024).split(b";")[0].strip() or b"0", 16)
                if size == 0:
                    while self.rfile.readline(1024).strip():
                        pass   # trailers
                    return data
                if len(data) + size > MAX_BODY:
                    raise ValueError("the body is over %d bytes" % MAX_BODY)
                data += self.rfile.read(size)
                self.rfile.readline(1024)
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise ValueError("the body is over %d bytes" % MAX_BODY)
        return self.rfile.read(length) if length > 0 else b""

    def handle_hook(self):
        # Exactly one answer per request, whatever happens before it: it's sent from the finally, and only there.
        started = time.time()
        name = "a hook"
        try:
            hook = self.path.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
            name = hook if hook in HOOKS else repr(self.path[:80])
            try:
                body = self.read_body()
            except (ValueError, OSError) as error:
                log("%s: unreadable body: %s" % (name, error))
                body = b""
                self.close_connection = True
            worker, budget = None, 0
            if hook == "run":
                worker, budget = self.server.mounter.run_hook(body), self.server.options.run_budget
            elif hook == "resume":
                worker, budget = self.server.mounter.resume_hook(), self.server.options.resume_budget
            if worker is not None:
                worker.join(budget)
                if worker.is_alive():
                    log("%s: still mounting after %ss; answering now" % (name, budget))
        except Exception as error:   # a hook must never fail
            log("%s: %r" % (name, error))
        finally:
            try:
                self.answer()
                log("%s: answered 200 after %.1fs" % (name, time.time() - started))
            except OSError as error:   # the caller hung up: nothing more to send it
                log("%s: couldn't answer: %r" % (name, error))
                self.close_connection = True

    def answer(self):
        payload = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    do_POST = do_GET = do_PUT = do_HEAD = handle_hook


class Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def options(argv):
    parser = argparse.ArgumentParser(description="MicroVM Studio's lifecycle hook listener")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9100)
    parser.add_argument("--status", default="/run/microvm-studio/mount-status")
    parser.add_argument("--lock", default="/run/microvm-studio-mount.lock")
    parser.add_argument("--mount-point", default="/workspace")
    parser.add_argument("--mount-timeout", type=int, default=45)
    parser.add_argument("--run-budget", type=float, default=50)
    parser.add_argument("--resume-budget", type=float, default=20)
    return parser.parse_args(argv)


def main(argv):
    settings = options(argv)
    server = Server((settings.bind, settings.port), Handler)
    server.options = settings
    server.mounter = Mounter(settings)
    log("listening on %s:%d" % server.server_address[:2])
    server.serve_forever()


if __name__ == "__main__":
    main(sys.argv[1:])
