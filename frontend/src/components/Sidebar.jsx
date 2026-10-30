import Icon from './Icon';

export default function Sidebar({ expanded, toggle, view, navigate, hasAnalysis }) {
  const items = [
    ['entrada', 'Nova reunião', 'file'], ['dashboard', 'Dashboard', 'grid'],
    ['historico', 'Histórico', 'archive'], ['assistente', 'Assistente', 'chat'],
  ];
  return <>
    {expanded && <button className="sidebar-backdrop" onClick={toggle} aria-label="Recolher menu" />}
    <aside className={`sidebar ${expanded ? 'is-expanded' : 'is-collapsed'}`}>
      <div className="sidebar-brand"><div className="brand-symbol">c<span>·</span></div><div className="sidebar-copy"><strong>Compiler<span>AI</span></strong><small>Meeting intelligence</small></div></div>
      <button className="sidebar-toggle" onClick={toggle} aria-expanded={expanded} aria-controls="side-navigation" aria-label={expanded ? 'Recolher menu' : 'Expandir menu'} title={expanded ? 'Recolher menu' : 'Expandir menu'}><Icon name="chevron" size={16} /></button>
      <div className="sidebar-section-label sidebar-copy">WORKSPACE</div>
      <nav id="side-navigation" aria-label="Navegação principal">{items.map(([key, label, icon]) => {
        const disabled = !hasAnalysis && ['dashboard', 'assistente'].includes(key);
        return <button key={key} type="button" disabled={disabled} className={`sidebar-item ${view === key ? 'active' : ''}`} onClick={() => navigate(key)} title={disabled ? `${label}: analise uma reunião primeiro` : label} aria-label={label} aria-current={view === key ? 'page' : undefined}><Icon name={icon} /><span className="sidebar-copy">{label}</span></button>;
      })}</nav>
      <div className="sidebar-bottom"><div className="workspace-avatar">C</div><div className="sidebar-copy"><strong>Meu workspace</strong><small>Conversas & perspectivas</small></div><span className="online-dot" /></div>
    </aside>
  </>;
}
