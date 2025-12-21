import React from 'react'

function Footer() {
  return (
    <footer className="bg-gray-100 py-4" data-testid="footer">
      <div className="container mx-auto px-4 text-center text-gray-600">
        <p>&copy; {new Date().getFullYear()} {{ENV_TITLE}}. Generated Environment.</p>
      </div>
    </footer>
  )
}

export default Footer
