import { AuthProvider, useAuth } from './store/AuthContext';
import MainLayout from './layout/MainLayout';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login'; // Bu dosyayı pages altına ekleyebilirsin

const AppContent = () => {
  const { user } = useAuth();
  
  // Eğer kullanıcı yoksa sadece Login sayfasını göster
  if (!user) return <Login />;

  return <MainLayout />;
};

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
