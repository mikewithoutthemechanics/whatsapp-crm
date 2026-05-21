const fs = require('fs');
const path = require('path');

/**
 * Prepare the www/ directory for Capacitor native builds.
 *
 * Steps:
 *  1. next build && next export   → generates out/
 *  2. Copies out/           → www/
 *  3. Overwrites www/index.html with a minimal redirect to /dashboard
 *     so the native app starts on the dashboard, not the login page.
 */

function copyRecursive(src, dest) {
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      fs.mkdirSync(d, { recursive: true });
      copyRecursive(s, d);
    } else {
      fs.copyFileSync(s, d);
    }
  }
}

function prepare() {
  if (!fs.existsSync('out')) {
    console.error('❌ out/ not found. Run: npx next build && npx next export');
    process.exit(1);
  }

  // Nuke old www/ and copy from out/
  fs.rmSync('www', { force: true, recursive: true });
  copyRecursive('out', 'www');

  // Overwrite the root index.html: native app opens on /dashboard directly
  const rootIndex = path.join('www', 'index.html');
  fs.writeFileSync(rootIndex, `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/>
  <meta name="theme-color" content="#25D366"/>
  <meta name="apple-mobile-web-app-capable" content="yes"/>
  <title>WhatsApp CRM SA</title>
  <style>
    body{margin:0;background:#0B0B0F;display:flex;align-items:center;justify-content:center;height:100vh}
    .loader{width:28px;height:28px;border:3px solid rgba(255,255,255,.12);border-top-color:#25D366;border-radius:50%;animation:spin .7s linear infinite}
    @keyframes spin{to{transform:rotate(360deg)}}
  </style>
  <script>window.location.replace('/dashboard')</script>
</head>
<body><div class="loader"></div></body>
</html>\n`);

  console.log('✅ www/ ready — run `npx cap sync && npx cap open android` (or: ios)');
}

prepare();
