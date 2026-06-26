import { NavLink, useNavigate } from 'react-router-dom'

export default function Nav() {
  const navigate = useNavigate()
  return (
    <nav>
      <NavLink to="/" className="nav-logo">🌵 Xena</NavLink>
      <NavLink to="/"            className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>Home</NavLink>
      <NavLink to="/field-trips" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>Field trips</NavLink>
      <NavLink to="/curiosity"   className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>Curiosity</NavLink>
      <NavLink to="/proposals"   className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>Proposals</NavLink>
      <div className="nav-spacer" />
      <button className="nav-add" onClick={() => navigate('/add')}>+ Add observation</button>
    </nav>
  )
}
