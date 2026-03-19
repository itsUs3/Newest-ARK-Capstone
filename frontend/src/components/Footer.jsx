import { FiGithub, FiLinkedin, FiMail } from 'react-icons/fi'

export default function Footer() {
  return (
    <footer className="border-t border-slate-700 glass-effect mt-20 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          <div>
            <h3 className="text-xl font-bold gradient-text mb-4">🏠 myNivas</h3>
            <p className="text-slate-400">AI-powered real estate aggregator solving property fragmentation in India.</p>
          </div>
          
          <div>
            <h4 className="font-bold text-white mb-4">Features</h4>
            <ul className="space-y-2 text-slate-400 text-sm">
              <li><a href="/search" className="hover:text-indigo-400">Property Search</a></li>
              <li><a href="/price-analyzer" className="hover:text-indigo-400">Price Analysis</a></li>
              <li><a href="/fraud-detector" className="hover:text-indigo-400">Fraud Detection</a></li>
              <li><a href="/advisor" className="hover:text-indigo-400">AI Advisor</a></li>
            </ul>
          </div>

          <div>
            <h4 className="font-bold text-white mb-4">Quick Links</h4>
            <ul className="space-y-2 text-slate-400 text-sm">
              <li><a href="/" className="hover:text-indigo-400">Home</a></li>
              <li><a href="/search" className="hover:text-indigo-400">Search</a></li>
              <li><a href="#" className="hover:text-indigo-400">About</a></li>
              <li><a href="#" className="hover:text-indigo-400">Contact</a></li>
            </ul>
          </div>

          <div>
            <h4 className="font-bold text-white mb-4">Follow Us</h4>
            <div className="flex gap-4 text-2xl">
              <a href="#" className="text-slate-400 hover:text-indigo-400 transition">
                <FiGithub />
              </a>
              <a href="#" className="text-slate-400 hover:text-indigo-400 transition">
                <FiLinkedin />
              </a>
              <a href="#" className="text-slate-400 hover:text-indigo-400 transition">
                <FiMail />
              </a>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-700 pt-8 text-center text-slate-400 text-sm">
          <p>&copy; 2026 myNivas. All rights reserved. Built with ❤️ for Indian real estate.</p>
        </div>
      </div>
    </footer>
  )
}
