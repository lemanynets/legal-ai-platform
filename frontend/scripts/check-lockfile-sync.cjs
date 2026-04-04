const fs = require("fs");
const path = require("path");

const root = process.cwd();
const packagePath = path.join(root, "package.json");
const lockPath = path.join(root, "package-lock.json");

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

if (!fs.existsSync(packagePath) || !fs.existsSync(lockPath)) {
  console.error("package.json or package-lock.json is missing.");
  process.exit(1);
}

const pkg = readJson(packagePath);
const lock = readJson(lockPath);

const manifestDeps = {
  ...(pkg.dependencies || {}),
  ...(pkg.devDependencies || {}),
  ...(pkg.optionalDependencies || {}),
};

const rootPackage = (lock.packages && lock.packages[""]) || {};
const lockDeps = {
  ...(rootPackage.dependencies || {}),
  ...(rootPackage.devDependencies || {}),
  ...(rootPackage.optionalDependencies || {}),
};

const missingInLock = [];
const versionMismatch = [];

for (const [name, version] of Object.entries(manifestDeps)) {
  if (!(name in lockDeps)) {
    missingInLock.push(name);
    continue;
  }
  if (lockDeps[name] !== version) {
    versionMismatch.push(`${name} (package.json: ${version}, lock: ${lockDeps[name]})`);
  }
}

if (missingInLock.length > 0 || versionMismatch.length > 0) {
  if (missingInLock.length > 0) {
    console.error(`Missing in lockfile: ${missingInLock.join(", ")}`);
  }
  if (versionMismatch.length > 0) {
    console.error("Version mismatches:");
    versionMismatch.forEach((line) => console.error(`  - ${line}`));
  }
  console.error("Lockfile is out of sync. Run `npm install` and commit package-lock.json.");
  process.exit(1);
}

console.log("Lockfile precheck passed.");
