import { useAuth } from '../store/AuthContext';
import { Navigate } from 'react-router-dom';

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" />; // Giriş yapmamışsa login'e at
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <h1>Bu sayfaya yetkiniz yok!</h1>; // Yetkisi yoksa uyarı ver
  }

  return children;
};

export default ProtectedRoute;
