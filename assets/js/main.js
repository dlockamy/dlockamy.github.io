// ============================================================
// dlockamy.github.io — Mission Console JS
// ============================================================

// --- CLOCK ---
function tick() {
  const t = new Date().toTimeString().slice(0, 8);
  ['nav-clock', 'footer-time'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = id === 'footer-time' ? 'SYS TIME: ' + t : t;
  });
}
tick();
setInterval(tick, 1000);

// --- KEYBOARD ROW ---
(function buildKeyboard() {
  const row = document.getElementById('keyboard-row');
  if (!row) return;
  const colors = [
    '#1a3a30','#2a1010','#1a2a10','#0a1a20',
    '#2a2010','#0f2230','#251510','#102218'
  ];
  const widths = [
    24,16,20,32,16,28,20,36,16,24,32,20,16,28,40,
    16,24,20,32,16,28,20,36,24,16,32,20,16,28,24,
    40,16,20,28,16,32,20,24,16,28,20,36,16,24,20,
    32,16,28,40,16,24,32,20,16,28,20,24,36,16,20
  ];
  widths.forEach((w, i) => {
    const key = document.createElement('div');
    key.className = 'key';
    key.style.cssText = `width:${w}px;background:${colors[i % colors.length]};`;
    row.appendChild(key);
  });
})();

// --- GITHUB API: repo count + recent commits ---
(function fetchGitHub() {
  const username = 'dlockamy';

  // Repo count
  fetch(`https://api.github.com/users/${username}`)
    .then(r => r.json())
    .then(data => {
      const el = document.getElementById('repo-count');
      if (el && data.public_repos !== undefined) {
        el.textContent = String(data.public_repos).padStart(3, '0');
      }
    })
    .catch(() => {});

  // Recent commits across repos (events API)
  fetch(`https://api.github.com/users/${username}/events/public?per_page=30`)
    .then(r => r.json())
    .then(events => {
      const log = document.getElementById('commit-log');
      if (!log) return;

      const pushes = events
        .filter(e => e.type === 'PushEvent' && e.payload.commits?.length)
        .slice(0, 5);

      if (!pushes.length) return;

      let html = `<div><span class="terminal__comment"># git log --oneline --all</span></div>`;
      pushes.forEach(push => {
        push.payload.commits.slice(0, 1).forEach(commit => {
          const sha = commit.sha.slice(0, 7);
          const msg = commit.message.split('\n')[0].slice(0, 52);
          const repo = push.repo.name.replace(`${username}/`, '');
          html += `<div><span class="terminal__cmd">${sha}</span> [${repo}] ${msg}</div>`;
        });
      });
      html += `<div style="margin-top:0.4rem"><span class="terminal__comment">$ _</span><span class="cursor-blink"></span></div>`;
      log.innerHTML = html;
    })
    .catch(() => {});
})();

// --- SKILL BAR ANIMATION ON SCROLL ---
(function animateSkills() {
  const bars = document.querySelectorAll('.skill-bar-fill');
  if (!bars.length) return;

  // Store target widths and set to 0 initially
  bars.forEach(bar => {
    bar.dataset.target = bar.style.width;
    bar.style.width = '0';
  });

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const bar = entry.target;
        setTimeout(() => { bar.style.width = bar.dataset.target; }, 100);
        observer.unobserve(bar);
      }
    });
  }, { threshold: 0.3 });

  bars.forEach(bar => observer.observe(bar));
})();

// --- PROJECT ENTRY HOVER SOUND (subtle) ---
// Intentionally silent — preserving the mission control calm
