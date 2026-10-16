import { mkdir, copyFile } from 'node:fs/promises';

// Publish only browser assets. API handlers are built separately by Vercel.
const destination = new URL('../public/', import.meta.url);
await mkdir(destination, { recursive: true });
for (const file of ['index.html', 'app.js', 'styles.css', 'favicon.svg']) {
  await copyFile(new URL(`../${file}`, import.meta.url), new URL(file, destination));
}
console.log('Built browser assets in public/');
