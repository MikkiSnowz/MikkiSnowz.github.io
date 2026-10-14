import { Link, Route, Routes } from 'react-router-dom';
import MenuPage from './pages/MenuPage.jsx';
import CheckoutPage from './pages/CheckoutPage.jsx';
import OrderStatusPage from './pages/OrderStatusPage.jsx';
import StaffPage from './pages/StaffPage.jsx';

function Home() {
  return (
    <main className="page narrow center">
      <h1>Welcome</h1>
      <p>Scan the QR code on your table to order.</p>
      <Link className="button" to="/takeaway">
        Order takeaway
      </Link>
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/t/:tableToken" element={<MenuPage />} />
      <Route path="/takeaway" element={<MenuPage />} />
      <Route path="/checkout" element={<CheckoutPage />} />
      <Route path="/order/:publicId" element={<OrderStatusPage />} />
      <Route path="/staff" element={<StaffPage />} />
      <Route path="*" element={<Home />} />
    </Routes>
  );
}
