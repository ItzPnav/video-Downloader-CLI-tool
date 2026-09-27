/* ============================================================
   utils.js — URL parsing & platform detection helpers
   ============================================================ */

function getEmbedUrl(url) {
  let u;
  try { u = new URL(url); } catch { return null; }

  // YouTube — watch page or short URL
  const isYT = /youtube\.com|youtu\.be/.test(u.hostname);
  if (isYT) {
    let vid = u.searchParams.get('v');
    if (!vid && u.hostname === 'youtu.be') vid = u.pathname.replace('/', '');
    if (!vid) {
      const m = u.pathname.match(/\/embed\/([^/?]+)/);
      if (m) vid = m[1];
    }
    if (vid) return `https://www.youtube.com/embed/${vid}?rel=0&autoplay=1`;
  }

  // Vimeo
  if (/vimeo\.com/.test(u.hostname)) {
    const m = u.pathname.match(/\/(\d+)/);
    if (m) return `https://player.vimeo.com/video/${m[1]}?autoplay=1`;
  }

  return null;
}

function isDirectVideo(url) {
  return /\.(mp4|webm|ogg|ogv|mov|m4v)(\?.*)?$/i.test(url);
}

function detectSource(url) {
  try {
    const u = new URL(url);
    if (/youtube\.com|youtu\.be/.test(u.hostname)) return 'youtube';
    if (/vimeo\.com/.test(u.hostname)) return 'vimeo';
    if (isDirectVideo(url)) return 'direct';
    return 'unknown';
  } catch {
    return 'unknown';
  }
}

function sourceLabel(source) {
  const map = {
    youtube: 'YouTube',
    vimeo:   'Vimeo',
    direct:  'Direct Video Stream',
    unknown: 'Media URL',
  };
  return map[source] || source;
}

function truncateUrl(url, max = 55) {
  return url.length > max ? url.slice(0, max) + '…' : url;
}
