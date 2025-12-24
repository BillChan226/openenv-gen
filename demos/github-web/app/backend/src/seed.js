import bcrypt from 'bcryptjs'
import { sequelize } from './config/database.js'
import { User, Repository, Issue } from './models/index.js'

async function seed() {
  try {
    await sequelize.authenticate()
    console.log('Connected to database')

    // Create users
    const hashedPassword = await bcrypt.hash('password123', 10)

    const users = await User.bulkCreate([
      {
        username: 'octocat',
        email: 'octocat@github.com',
        password: hashedPassword,
        name: 'The Octocat',
        bio: 'GitHub mascot and code enthusiast',
        avatar_url: 'https://avatars.githubusercontent.com/u/583231?v=4',
        location: 'San Francisco, CA',
      },
      {
        username: 'torvalds',
        email: 'torvalds@linux.org',
        password: hashedPassword,
        name: 'Linus Torvalds',
        bio: 'Creator of Linux and Git',
        avatar_url: 'https://avatars.githubusercontent.com/u/1024025?v=4',
        location: 'Portland, OR',
      },
      {
        username: 'gaearon',
        email: 'dan@react.dev',
        password: hashedPassword,
        name: 'Dan Abramov',
        bio: 'Working on React',
        avatar_url: 'https://avatars.githubusercontent.com/u/810438?v=4',
        location: 'London, UK',
      },
    ])

    console.log(`Created ${users.length} users`)

    // Create repositories
    const repos = await Repository.bulkCreate([
      {
        owner_id: users[0].id,
        name: 'hello-world',
        description: 'My first repository on GitHub!',
        is_private: false,
        language: 'Markdown',
        stars_count: 2543,
        forks_count: 1821,
      },
      {
        owner_id: users[0].id,
        name: 'spoon-knife',
        description: 'This repo is for demonstration purposes only.',
        is_private: false,
        language: 'HTML',
        stars_count: 12100,
        forks_count: 143000,
      },
      {
        owner_id: users[1].id,
        name: 'linux',
        description: 'Linux kernel source tree',
        is_private: false,
        language: 'C',
        stars_count: 175000,
        forks_count: 52000,
      },
      {
        owner_id: users[1].id,
        name: 'git',
        description: 'Git Source Code Mirror - Fast version control system',
        is_private: false,
        language: 'C',
        stars_count: 51000,
        forks_count: 25000,
      },
      {
        owner_id: users[2].id,
        name: 'redux',
        description: 'Predictable state container for JavaScript apps',
        is_private: false,
        language: 'TypeScript',
        stars_count: 60500,
        forks_count: 15600,
      },
      {
        owner_id: users[2].id,
        name: 'overreacted.io',
        description: 'Personal blog by Dan Abramov',
        is_private: false,
        language: 'JavaScript',
        stars_count: 7000,
        forks_count: 1200,
      },
    ])

    console.log(`Created ${repos.length} repositories`)

    // Create some issues
    const issues = await Issue.bulkCreate([
      {
        repository_id: repos[0].id,
        author_id: users[1].id,
        title: 'Add more examples to README',
        body: 'It would be helpful to have more examples in the README file.',
        status: 'open',
        issue_number: 1,
      },
      {
        repository_id: repos[2].id,
        author_id: users[0].id,
        title: 'Kernel panic on ARM64',
        body: 'Getting kernel panic when booting on ARM64 device.',
        status: 'open',
        issue_number: 1,
      },
      {
        repository_id: repos[4].id,
        author_id: users[0].id,
        title: 'TypeScript types not working correctly',
        body: 'The TypeScript types seem to be incorrect for the connect function.',
        status: 'closed',
        issue_number: 1,
      },
    ])

    console.log(`Created ${issues.length} issues`)
    console.log('\nSeed completed successfully!')
    console.log('\nYou can login with any of these accounts:')
    console.log('  - octocat / password123')
    console.log('  - torvalds / password123')
    console.log('  - gaearon / password123')

    process.exit(0)
  } catch (error) {
    console.error('Seed failed:', error)
    process.exit(1)
  }
}

seed()
