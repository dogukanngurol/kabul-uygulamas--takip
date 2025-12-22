/* Temel Reset ve Layout */
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
body, html, #root { height: 100%; background-color: #f4f7f6; }

/* Layout Yapısı */
.app-container { display: flex; height: 100vh; }
.sidebar { width: 250px; background-color: #2c3e50; color: white; display: flex; flex-direction: column; flex-shrink: 0; }
.sidebar-header { padding: 20px; font-size: 1.2rem; font-weight: bold; background-color: #1a252f; text-align: center; }
.menu-item { padding: 15px 20px; cursor: pointer; border-bottom: 1px solid #34495e; transition: background 0.3s; }
.menu-item:hover, .menu-item.active { background-color: #34495e; border-left: 4px solid #3498db; }
.main-content { flex-grow: 1; display: flex; flex-direction: column; overflow: hidden; }
.top-bar { height: 60px; background-color: white; border-bottom: 1px solid #ddd; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; }
.content-area { padding: 20px; overflow-y: auto; height: 100%; }

/* Form ve Tablo Stilleri */
.card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 20px; }
.btn { padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
.btn-primary { background-color: #3498db; color: white; }
.btn-danger { background-color: #e74c3c; color: white; }
.input-group { margin-bottom: 15px; }
.input-group label { display: block; margin-bottom: 5px; font-weight: 600; }
.input-group input, .input-group select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; }
th, td { text-align: left; padding: 12px; border-bottom: 1px solid #eee; }
th { background-color: #f8f9fa; }
.status-badge { padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; }
.status-acik { background-color: #e3f2fd; color: #1565c0; }
.status-tamamlandi { background-color: #e8f5e9; color: #2e7d32; }

/* Login Ekranı */
.login-overlay { position: fixed; top:0; left:0; width:100%; height:100%; background:#2c3e50; display:flex; justify-content:center; align-items:center; z-index: 1000; }
.login-box { background: white; padding: 40px; border-radius: 8px; width: 400px; text-align: center; }
.role-btn { display: block; width: 100%; padding: 10px; margin: 10px 0; background: #ecf0f1; border: 1px solid #bdc3c7; cursor: pointer; text-align: left; transition: 0.2s; }
.role-btn:hover { background: #dfe6e9; border-color: #3498db; }
import React, { useState, useEffect, useContext, createContext } from 'react';
import './App.css';

// --- 1. MOCK VERİLER VE SABİTLER ---
const ROLES = {
  ADMIN: 'Admin',
  MANAGER: 'Yönetici',
  DIRECTOR: 'Müdür',
  FIELD: 'Saha Personeli'
};

const INITIAL_DATA = [
  { id: 1, title: 'İstanbul Depo Sayımı', status: 'Açık', assignedTo: 'Saha Personeli', createdBy: 'Yönetici', date: '2023-10-25' },
  { id: 2, title: 'Ankara Müşteri Ziyareti', status: 'Tamamlandı', assignedTo: 'Saha Personeli', createdBy: 'Müdür', date: '2023-10-24' },
  { id: 3, title: 'Q3 Finans Raporu', status: 'Açık', assignedTo: 'Yönetici', createdBy: 'Admin', date: '2023-10-26' },
];

// --- 2. ORTAK STATE (CONTEXT) ---
const AppContext = createContext();

const AppProvider = ({ children }) => {
  // Kullanıcı Oturumu
  const [user, setUser] = useState(null); // { name: 'Ali', role: 'Admin' }
  
  // İş Verileri (localStorage'dan okur veya mock yükler)
  const [tasks, setTasks] = useState(() => {
    const saved = localStorage.getItem('app_tasks');
    return saved ? JSON.parse(saved) : INITIAL_DATA;
  });

  // Navigasyon State'i
  const [currentView, setCurrentView] = useState('dashboard');

  // Veri her değiştiğinde localStorage güncelle
  useEffect(() => {
    localStorage.setItem('app_tasks', JSON.stringify(tasks));
  }, [tasks]);

  // Giriş Yapma
  const login = (role) => {
    setUser({ name: 'Demo Kullanıcı', role });
    setCurrentView('dashboard');
  };

  // Çıkış Yapma
  const logout = () => {
    setUser(null);
    setCurrentView('dashboard');
  };

  // Yeni İş Ekleme
  const addTask = (task) => {
    const newTask = { ...task, id: Date.now(), status: 'Açık', date: new Date().toISOString().split('T')[0] };
    setTasks([newTask, ...tasks]);
  };

  // İş Durumu Güncelleme
  const updateStatus = (id, newStatus) => {
    setTasks(tasks.map(t => t.id === id ? { ...t, status: newStatus } : t));
  };

  return (
    <AppContext.Provider value={{ user, login, logout, tasks, addTask, updateStatus, currentView, setCurrentView }}>
      {children}
    </AppContext.Provider>
  );
};

// --- 3. BİLEŞENLER (COMPONENTS) ---

// Giriş Ekranı
const LoginScreen = () => {
  const { login } = useContext(AppContext);
  return (
    <div className="login-overlay">
      <div className="login-box">
        <h2>Demo Giriş</h2>
        <p>Lütfen test etmek istediğiniz rolü seçin:</p>
        <button className="role-btn" onClick={() => login(ROLES.ADMIN)}>🔑 <strong>Admin</strong> (Tam Yetki)</button>
        <button className="role-btn" onClick={() => login(ROLES.MANAGER)}>📁 <strong>Yönetici</strong> (İş Atar, Rapor Görür)</button>
        <button className="role-btn" onClick={() => login(ROLES.DIRECTOR)}>📊 <strong>Müdür</strong> (Sadece İzler ve Raporlar)</button>
        <button className="role-btn" onClick={() => login(ROLES.FIELD)}>🚚 <strong>Saha Personeli</strong> (İşlerini Görür)</button>
      </div>
    </div>
  );
};

// Sol Menü
const Sidebar = () => {
  const { user, currentView, setCurrentView } = useContext(AppContext);
  
  // Role göre menü filtreleme
  const menuItems = [
    { id: 'dashboard', label: 'Özet Tablo', roles: [ROLES.ADMIN, ROLES.MANAGER, ROLES.DIRECTOR, ROLES.FIELD] },
    { id: 'taskList', label: 'İş Listesi', roles: [ROLES.ADMIN, ROLES.MANAGER, ROLES.FIELD] },
    { id: 'createTask', label: 'Yeni İş Oluştur', roles: [ROLES.ADMIN, ROLES.MANAGER] },
    { id: 'reports', label: 'Raporlar', roles: [ROLES.ADMIN, ROLES.DIRECTOR] },
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-header">İş Takip v1.0</div>
      {menuItems.filter(item => item.roles.includes(user.role)).map(item => (
        <div 
          key={item.id} 
          className={`menu-item ${currentView === item.id ? 'active' : ''}`}
          onClick={() => setCurrentView(item.id)}
        >
          {item.label}
        </div>
      ))}
    </div>
  );
};

// 4. EKRANLAR (VIEWS)

const Dashboard = () => {
  const { tasks, user } = useContext(AppContext);
  
  // Basit istatistikler
  const totalTasks = tasks.length;
  const completedTasks = tasks.filter(t => t.status === 'Tamamlandı').length;
  
  return (
    <div className="card">
      <h2>Hoşgeldiniz, {user.role}</h2>
      <p>Sistem özeti aşağıdadır:</p>
      <div style={{ display: 'flex', gap: '20px', marginTop: '20px' }}>
        <div style={{ background: '#3498db', color: 'white', padding: '20px', borderRadius: '8px', flex: 1 }}>
          <h3>Toplam İş</h3>
          <h1>{totalTasks}</h1>
        </div>
        <div style={{ background: '#2ecc71', color: 'white', padding: '20px', borderRadius: '8px', flex: 1 }}>
          <h3>Tamamlanan</h3>
          <h1>{completedTasks}</h1>
        </div>
      </div>
    </div>
  );
};

const TaskList = () => {
  const { tasks, user, updateStatus } = useContext(AppContext);
  
  // Saha personeli sadece kendine atananları veya genel işleri görür (Demo için hepsini gösteriyoruz ama filtreleyebiliriz)
  const filteredTasks = user.role === ROLES.FIELD 
    ? tasks // Normalde: tasks.filter(t => t.assignedTo === 'Saha Personeli')
    : tasks;

  return (
    <div className="card">
      <h3>İş Listesi</h3>
      <table>
        <thead>
          <tr>
            <th>Başlık</th>
            <th>Atanan</th>
            <th>Durum</th>
            <th>İşlem</th>
          </tr>
        </thead>
        <tbody>
          {filteredTasks.map(task => (
            <tr key={task.id}>
              <td>{task.title}</td>
              <td>{task.assignedTo}</td>
              <td>
                <span className={`status-badge status-${task.status.toLowerCase().replace('ı', 'i')}`}>
                  {task.status}
                </span>
              </td>
              <td>
                {task.status !== 'Tamamlandı' && (
                  <button className="btn btn-primary" style={{ fontSize: '12px', padding: '5px 10px' }} 
                    onClick={() => updateStatus(task.id, 'Tamamlandı')}>
                    Tamamla
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const CreateTask = () => {
  const { addTask, setCurrentView, user } = useContext(AppContext);
  const [title, setTitle] = useState('');
  const [assignedTo, setAssignedTo] = useState('Saha Personeli');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!title) return;
    
    addTask({
      title,
      assignedTo,
      createdBy: user.role
    });
    
    alert('İş başarıyla oluşturuldu!');
    setCurrentView('taskList');
  };

  return (
    <div className="card">
      <h3>Yeni İş Oluştur</h3>
      <form onSubmit={handleSubmit}>
        <div className="input-group">
          <label>İş Başlığı</label>
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Örn: Müşteri teslimatı..." />
        </div>
        <div className="input-group">
          <label>Kime Atanacak?</label>
          <select value={assignedTo} onChange={(e) => setAssignedTo(e.target.value)}>
            <option>Saha Personeli</option>
            <option>Yönetici</option>
            <option>Teknik Ekip</option>
          </select>
        </div>
        <button type="submit" className="btn btn-primary">Kaydet</button>
      </form>
    </div>
  );
};

const Reports = () => {
  return (
    <div className="card">
      <h3>Sistem Raporları</h3>
      <p>Bu alan sadece Admin ve Müdür yetkisine açıktır.</p>
      <hr style={{margin: '15px 0'}} />
      <p>Burada grafikler ve Excel döküm butonları yer alacak.</p>
    </div>
  );
};

// --- 5. ANA LAYOUT VE RENDER ---

const MainLayout = () => {
  const { user, logout, currentView } = useContext(AppContext);

  // Eğer kullanıcı yoksa Login ekranını göster
  if (!user) return <LoginScreen />;

  // View Router Mantığı
  const renderView = () => {
    switch (currentView) {
      case 'dashboard': return <Dashboard />;
      case 'taskList': return <TaskList />;
      case 'createTask': return <CreateTask />;
      case 'reports': return <Reports />;
      default: return <Dashboard />;
    }
  };

  return (
    <div className="app-container">
      <Sidebar />
      <div className="main-content">
        <div className="top-bar">
          <div><strong>{user.name}</strong> <span style={{fontSize:'0.8rem', color:'#7f8c8d'}}>({user.role})</span></div>
          <button onClick={logout} className="btn btn-danger" style={{ fontSize: '0.8rem' }}>Çıkış</button>
        </div>
        <div className="content-area">
          {renderView()}
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <AppProvider>
      <MainLayout />
    </AppProvider>
  );
}

export default App;
