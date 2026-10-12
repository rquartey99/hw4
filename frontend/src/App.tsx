import { Route, Routes } from 'react-router-dom'
import { useAuth } from './authContext.ts'
import ChatWidget from './components/ChatWidget.tsx'
import Footer from './components/Footer.tsx'
import Navbar from './components/Navbar.tsx'
import Account from './pages/Account.tsx'
import About from './pages/About.tsx'
import CreateAccount from './pages/CreateAccount.tsx'
import Home from './pages/Home.tsx'
import Login from './pages/Login.tsx'
import NotFound from './pages/NotFound.tsx'
import ProductDetail from './pages/ProductDetail.tsx'
import Products from './pages/Products.tsx'

export default function App() {
  const { user, loading } = useAuth()

  return (
    <>
      <Navbar />
      <main className="page">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/create-account" element={<CreateAccount />} />
          <Route path="/account" element={<Account />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
      {/* Remount the chat when the user changes, so saved chats load for the right person. */}
      {!loading && <ChatWidget key={user ? `user-${user.id}` : 'guest'} />}
    </>
  )
}
