// Google Analytics for this website (not the app, which collects nothing), behind a consent choice.
// Until a visitor accepts, analytics storage is denied: no analytics cookies are set and Google receives only
// cookieless pings. The choice is kept in this browser; "Cookie choices" in the footer asks again.
(function () {
  // The Google tag for this site. Its destinations, the Analytics property G-08P9R1QZJR among them, are set in
  // Google's tag settings, so there is no gtag('config') here.
  var ID = 'GTM-MFHMMZB2';
  var KEY = 'analytics-consent';
  var choice = null;
  try { choice = localStorage.getItem(KEY); } catch (e) {}

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag('consent', 'default', {
    analytics_storage: choice === 'granted' ? 'granted' : 'denied',
    ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied'
  });
  gtag('js', new Date());
  var tag = document.createElement('script');
  tag.async = true;
  tag.src = 'https://www.googletagmanager.com/gtm.js?id=' + ID;
  document.head.appendChild(tag);

  function decide(value) {
    try { localStorage.setItem(KEY, value); } catch (e) {}
    gtag('consent', 'update', { analytics_storage: value });
    var bar = document.getElementById('consent');
    if (bar) bar.remove();
  }

  function ask() {
    if (document.getElementById('consent')) return;
    var privacy = (document.querySelector('.site-footer a[href$="privacy.html"]') || {}).href || 'privacy.html';
    var bar = document.createElement('div');
    bar.id = 'consent';
    bar.setAttribute('role', 'region');
    bar.setAttribute('aria-label', 'Analytics cookies');
    var text = document.createElement('p');
    text.append('This website uses Google Analytics cookies to count visits, if you accept. The app itself collects nothing. ');
    var link = document.createElement('a');
    link.href = privacy;
    link.textContent = 'Privacy policy';
    text.append(link, '.');
    var buttons = document.createElement('div');
    [['Decline', 'denied', 'button secondary'], ['Accept', 'granted', 'button primary']].forEach(function (b) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = b[2];
      button.textContent = b[0];
      button.addEventListener('click', function () { decide(b[1]); });
      buttons.append(button);
    });
    bar.append(text, buttons);
    document.body.append(bar);
  }

  function ready() {
    if (choice !== 'granted' && choice !== 'denied') ask();
    var footer = document.querySelector('.site-footer nav');
    if (footer) {
      var again = document.createElement('a');
      again.href = '#';
      again.textContent = 'Cookie choices';
      again.addEventListener('click', function (event) { event.preventDefault(); ask(); });
      footer.append(again);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready); else ready();
})();
