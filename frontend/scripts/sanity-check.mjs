import fs from 'node:fs'
import path from 'node:path'

const rootDir = path.resolve(process.cwd(), 'src')
const appPath = path.join(rootDir, 'App.jsx')
const homePath = path.join(rootDir, 'pages', 'Home.jsx')
const apiPath = path.join(rootDir, 'utils', 'api.js')

const issues = []

function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true })
  const files = []

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      files.push(...walk(fullPath))
    } else if (entry.isFile()) {
      files.push(fullPath)
    }
  }

  return files
}

for (const file of walk(rootDir)) {
  const content = fs.readFileSync(file, 'utf8')

  if (content.includes('http://localhost:8000') || content.includes('https://localhost:8000')) {
    issues.push(`${path.relative(process.cwd(), file)} still hardcodes localhost API URLs`)
  }

  if (file !== apiPath && content.includes("import axios from 'axios'")) {
    issues.push(`${path.relative(process.cwd(), file)} still imports axios directly instead of using utils/api.js`)
  }
}

const appContent = fs.readFileSync(appPath, 'utf8')
if (!appContent.includes('path="/property/:id"')) {
  issues.push('frontend route for property details is missing "/property/:id"')
}

const homeContent = fs.readFileSync(homePath, 'utf8')
if (homeContent.includes("navigate('/property')") || homeContent.includes('navigate("/property")')) {
  issues.push('Home page still navigates to the broken "/property" route')
}

if (issues.length > 0) {
  console.error('Frontend sanity check failed:')
  for (const issue of issues) {
    console.error(`- ${issue}`)
  }
  process.exit(1)
}

console.log('Frontend sanity check passed.')
