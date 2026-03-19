import { Link } from 'react-router-dom'
import { FiMenu, FiX, FiSearch, FiTrendingUp, FiShield, FiMessageCircle, FiMapPin, FiCheckSquare, FiLayout, FiDollarSign, FiChevronDown, FiFileText } from 'react-icons/fi'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false)
  const [activeDropdown, setActiveDropdown] = useState(null)

  const navStructure = [
    { label: 'Search', path: '/search', icon: FiSearch },
    { label: 'Market News', path: '/market-news', icon: FiTrendingUp },
    {
      label: 'Analysis Tools',
      icon: FiDollarSign,
      dropdown: [
        { label: 'Price Analyzer', path: '/price-analyzer', icon: FiDollarSign },
        { label: 'Fraud Detector', path: '/fraud-detector', icon: FiShield },
        { label: 'Investment Analyzer', path: '/investment-analyzer', icon: FiTrendingUp },
        { label: 'Contract Analyzer', path: '/contract-analyzer', icon: FiFileText },
      ]
    },
    {
      label: 'AI Features',
      icon: FiMessageCircle,
      dropdown: [
        { label: 'AI Advisor Chat', path: '/advisor', icon: FiMessageCircle },
        { label: 'Location Booster', path: '/location-booster', icon: FiMapPin },
        { label: 'Amenity Matcher', path: '/amenity-matcher', icon: FiCheckSquare },
        { label: 'Vastu Checker', path: '/vastu-checker', icon: FiCheckSquare },
      ]
    },
    { label: 'GNN Floor Plan', path: '/gnn-floorplan', icon: FiLayout },
  ]

  const handleDropdownToggle = (label) => {
    setActiveDropdown(activeDropdown === label ? null : label)
  }

  return (
    <nav className="sticky top-0 z-50 glass-effect border-b border-slate-700/50 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <motion.div
              whileHover={{ scale: 1.05 }}
              transition={{ type: "spring", stiffness: 400 }}
              className="text-2xl font-bold gradient-text flex items-center gap-2"
            >
              🏠 <span>myNivas</span>
            </motion.div>
          </Link>

          {/* Desktop Menu */}
          <div className="hidden lg:flex items-center gap-2">
            {navStructure.map((item) => (
              item.dropdown ? (
                <div key={item.label} className="relative">
                  <button
                    onClick={() => handleDropdownToggle(item.label)}
                    onMouseEnter={() => setActiveDropdown(item.label)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg text-slate-300 hover:bg-slate-700/50 hover:text-white transition-all duration-200"
                  >
                    <item.icon className="text-sm" />
                    <span className="text-sm font-medium">{item.label}</span>
                    <FiChevronDown className={`text-xs transition-transform ${activeDropdown === item.label ? 'rotate-180' : ''}`} />
                  </button>
                  
                  <AnimatePresence>
                    {activeDropdown === item.label && (
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.15 }}
                        onMouseLeave={() => setActiveDropdown(null)}
                        className="absolute top-full left-0 mt-1 w-56 bg-slate-800/95 backdrop-blur-xl border border-slate-700/50 rounded-xl shadow-2xl overflow-hidden"
                      >
                        {item.dropdown.map((subItem) => (
                          <Link
                            key={subItem.path}
                            to={subItem.path}
                            onClick={() => setActiveDropdown(null)}
                            className="flex items-center gap-3 px-4 py-3 text-slate-300 hover:bg-slate-700/50 hover:text-white transition-all duration-200 border-b border-slate-700/30 last:border-b-0"
                          >
                            <subItem.icon className="text-indigo-400" />
                            <span className="text-sm">{subItem.label}</span>
                          </Link>
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ) : (
                <Link
                  key={item.path}
                  to={item.path}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-slate-300 hover:bg-slate-700/50 hover:text-white transition-all duration-200"
                >
                  <item.icon className="text-sm" />
                  <span className="text-sm font-medium">{item.label}</span>
                </Link>
              )
            ))}
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="lg:hidden text-2xl text-white hover:text-indigo-400 transition"
          >
            {isOpen ? <FiX /> : <FiMenu />}
          </button>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="lg:hidden pb-4 space-y-1 overflow-hidden"
            >
              {navStructure.map((item) => (
                item.dropdown ? (
                  <div key={item.label}>
                    <button
                      onClick={() => handleDropdownToggle(item.label)}
                      className="w-full flex items-center justify-between gap-2 px-4 py-3 rounded-lg text-slate-300 hover:bg-slate-700/50 transition"
                    >
                      <div className="flex items-center gap-2">
                        <item.icon />
                        <span className="font-medium">{item.label}</span>
                      </div>
                      <FiChevronDown className={`text-xs transition-transform ${activeDropdown === item.label ? 'rotate-180' : ''}`} />
                    </button>
                    <AnimatePresence>
                      {activeDropdown === item.label && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="ml-4 mt-1 space-y-1 overflow-hidden"
                        >
                          {item.dropdown.map((subItem) => (
                            <Link
                              key={subItem.path}
                              to={subItem.path}
                              className="flex items-center gap-2 px-4 py-2 rounded-lg text-slate-400 hover:bg-slate-700/50 hover:text-white transition text-sm"
                              onClick={() => {
                                setIsOpen(false)
                                setActiveDropdown(null)
                              }}
                            >
                              <subItem.icon className="text-indigo-400" />
                              {subItem.label}
                            </Link>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                ) : (
                  <Link
                    key={item.path}
                    to={item.path}
                    className="flex items-center gap-2 px-4 py-3 rounded-lg text-slate-300 hover:bg-slate-700/50 transition"
                    onClick={() => setIsOpen(false)}
                  >
                    <item.icon />
                    <span className="font-medium">{item.label}</span>
                  </Link>
                )
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </nav>
  )
}
