# Run the original MPPT website
This is the pre-redesign snapshot of MPPT Lab, source commit 896965df93d2c1da182cce61185bccbfd1dc3d79.
The website code and model are unchanged. This guide and a GitHub Pages workflow were added for portability.

## Locally
Extract the ZIP, open a terminal in this folder and run:
python -m http.server 8000 --directory dist
Open http://localhost:8000 . Keep the terminal running.
On Windows, use py instead of python if needed.
Do not double-click index.html: its module workers and data fetches need a web server.
No npm install or build step is required.

## GitHub Pages
Create a GitHub repository, use main as its branch and upload the extracted contents (not the ZIP).
Include the .github/workflows/pages.yml file. If uploading through a browser hides this folder, create that exact path using Add file > Create new file and paste the supplied workflow.
In repository Settings > Pages, select GitHub Actions as the source.
Push to main or run the Deploy website to GitHub Pages workflow from Actions.
Its completed deployment provides the site URL. All site assets use relative paths, suitable for repository subpaths.
GitHub Pages availability depends on your repository visibility and plan.

## Verification
With Node.js installed:
node scripts/validate.mjs
node scripts/validate-upgrade.mjs

See README.md for the project equations, provenance and model limitations.
