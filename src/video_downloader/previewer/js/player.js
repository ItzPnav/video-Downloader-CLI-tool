/* ============================================================
   player.js — main video loading & player control logic
   ============================================================ */

const $ = id => document.getElementById(id);

const inputEl      = $('videoInput');
const playerSec    = $('playerSection');
const directWrap   = $('directWrap');
const iframeWrap   = $('iframeWrap');
const errorCard    = $('errorCard');
const errorMsgEl   = $('errorMsg');
const loaderCard   = $('loaderCard');
const metaBar      = $('metaBar');
const metaSourceEl = $('metaSource');
const metaLinkEl   = $('metaLink');
const videoTag     = $('videoTag');
const embedFrame   = $('embedFrame');

function showOnly(...visibles) {
  const all = [directWrap, iframeWrap, errorCard, loaderCard, metaBar];
  all.forEach(el => el.classList.remove('visible'));
  visibles.forEach(el => el && el.classList.add('visible'));
}

function setMeta(url, source) {
  metaSourceEl.textContent = `Source: ${sourceLabel(source)}`;
  metaLinkEl.href = url;
  metaBar.classList.add('visible');
}

function resetPlayer() {
  videoTag.pause();
  videoTag.src = '';
  videoTag.onerror = null;
  embedFrame.src = '';
  playerSec.classList.remove('visible');
  showOnly();
}

function loadVideo() {
  const raw = inputEl.value.trim();
  resetPlayer();

  if (!raw) {
    showError('Please enter a video URL.');
    return;
  }

  // Auto-prepend protocol if omitted
  let cleanUrl = raw;
  if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://') && !cleanUrl.startsWith('file://')) {
    cleanUrl = 'https://' + cleanUrl;
  }

  let parsedUrl;
  try {
    parsedUrl = new URL(cleanUrl);
  } catch {
    showError('Invalid URL. Please check the address.');
    return;
  }

  playerSec.classList.add('visible');
  showOnly(loaderCard);

  const source = detectSource(cleanUrl);

  if (source === 'youtube' || source === 'vimeo') {
    loadEmbed(cleanUrl, source);
  } else if (source === 'direct') {
    loadDirect(cleanUrl);
  } else {
    // Attempt direct video stream fallback
    loadDirect(cleanUrl);
  }
}

function loadEmbed(url, source) {
  const embedUrl = getEmbedUrl(url);
  if (!embedUrl) {
    showError('Could not generate an embed URL from this link.');
    return;
  }

  embedFrame.src = embedUrl;

  embedFrame.onload = () => {
    showOnly(iframeWrap, metaBar);
    iframeWrap.classList.add('visible');
    setMeta(url, source);
    addToHistory(url);
  };

  embedFrame.onerror = () => {
    showError('The embed failed to load. The platform may have restricted embedding for this video.');
  };

  setTimeout(() => {
    if (loaderCard.classList.contains('visible')) {
      showOnly(iframeWrap, metaBar);
      iframeWrap.classList.add('visible');
      setMeta(url, source);
      addToHistory(url);
    }
  }, 2500);
}

function loadDirect(url) {
  videoTag.src = url;

  videoTag.oncanplay = () => {
    showOnly(directWrap, metaBar);
    directWrap.classList.add('visible');
    setMeta(url, 'direct');
    addToHistory(url);
    videoTag.oncanplay = null;
  };

  videoTag.onerror = () => {
    showError(
      'Could not load direct video stream. Server may block cross-origin requests (CORS) or link is invalid.'
    );
    videoTag.onerror = null;
  };
}

function showError(msg) {
  playerSec.classList.add('visible');
  showOnly(errorCard);
  errorMsgEl.textContent = msg;
}

inputEl.addEventListener('keydown', e => {
  if (e.key === 'Enter') loadVideo();
});

inputEl.addEventListener('paste', () => {
  setTimeout(() => {
    const val = inputEl.value.trim();
    if (val.startsWith('http') || val.startsWith('www.')) loadVideo();
  }, 50);
});

// Check URL query parameter on initial load (e.g. ?url=...)
window.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const initialUrl = params.get('url') || params.get('v');
  if (initialUrl) {
    inputEl.value = initialUrl;
    loadVideo();
  }
});
