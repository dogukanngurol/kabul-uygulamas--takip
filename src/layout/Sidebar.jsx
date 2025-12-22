import { useAuth } from '../store/AuthContext';
import { ROLES, PERMISSIONS } from '../utils/roleUtils';

const Sidebar = ({ setCurrentPage }) => {
  const { user } = useAuth();

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', roles: Object.values(ROLES) },
    { id: 'users', label: 'Kullanıcılar', roles: PERMISSIONS.MANAGE_USERS },
    { id: 'reports', label: 'Raporlar', roles: PERMISSIONS.VIEW_REPORTS },
  ];

  return (
    <aside className="sidebar">
      {menuItems.filter(item => item.roles.includes(user.role)).map(item => (
        <button key={item.id} onClick={() => setCurrentPage(item.id)}>
          {item.label}
        </button>
      ))}
    </aside>
  );
};

export default Sidebar;
