import React, { useState } from 'react';

const Login = ({ onLoginSuccess }) => {
  const [mode, setMode] = useState('login'); // 'login' or 'register'
  const [username, setUsername] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [isTestnet, setIsTestnet] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const endpoint = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
    const payload = mode === 'register' 
      ? { username, api_key: apiKey, api_secret: apiSecret, is_testnet: isTestnet }
      : { username };

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (response.ok) {
        // Save token and user info to localStorage
        localStorage.setItem('authToken', data.token);
        localStorage.setItem('user', JSON.stringify(data.user));
        onLoginSuccess();
      } else {
        setError(data.detail || 'Error al conectar. Verifica tus credenciales.');
      }
    } catch (err) {
      setError('Error de Red: No se pudo conectar con el servidor.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="card login-card-inner">
        <h2 style={{ textAlign: 'center', marginBottom: '10px' }}>
          {mode === 'register' ? 'Registro de Usuario 🚀' : 'Iniciar Sesión 🔐'}
        </h2>
        
        {mode === 'register' && (
          <div style={{ 
            background: isTestnet ? 'rgba(76, 175, 80, 0.1)' : 'rgba(244, 67, 54, 0.1)', 
            padding: '10px', 
            borderRadius: '8px', 
            marginBottom: '20px',
            border: `1px solid ${isTestnet ? '#4caf50' : '#f44336'}`
          }}>
            <p style={{ color: isTestnet ? '#4caf50' : '#f44336', textAlign: 'center', margin: 0, fontWeight: 'bold' }}>
              {isTestnet ? 'MODO TESTNET (SIMULACIÓN)' : '⚠️ CUIDADO: MODO CUENTA REAL ⚠️'}
            </p>
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Nombre de Usuario</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Tu username"
              required
              className="login-input"
            />
          </div>

          {mode === 'register' && (
            <>
              <div className="form-group" style={{ marginTop: '20px' }}>
                <label>Entorno de Trading</label>
                <select 
                  className="login-input" 
                  value={isTestnet ? 'testnet' : 'real'}
                  onChange={(e) => setIsTestnet(e.target.value === 'testnet')}
                  style={{ width: '100%', cursor: 'pointer' }}
                >
                  <option value="testnet">Binance Testnet (Recomendado para pruebas)</option>
                  <option value="real">Binance Real (Cuenta Live - Dinero Real)</option>
                </select>
              </div>

              <div className="form-group" style={{ marginTop: '20px' }}>
                <label>API Key de Binance</label>
                <input
                  type="text"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Tu API Key"
                  required
                  className="login-input"
                />
              </div>

              <div className="form-group" style={{ marginTop: '20px' }}>
                <label>API Secret de Binance</label>
                <input
                  type="password"
                  value={apiSecret}
                  onChange={(e) => setApiSecret(e.target.value)}
                  placeholder="Tu API Secret"
                  required
                  className="login-input"
                />
              </div>
            </>
          )}
          
          {error && (
            <div 
              className="error-message" 
              style={{ 
                marginTop: '20px', 
                padding: '15px',
                background: 'rgba(255, 73, 118, 0.1)',
                border: '1px solid #ff4976',
                borderRadius: '8px',
                color: '#ff4976',
                fontSize: '0.9rem',
                lineHeight: '1.5'
              }}
            >
              <strong>⚠️ Error:</strong>
              <div style={{ marginTop: '8px' }}>{error}</div>
            </div>
          )}
          
          <button 
            type="submit" 
            className={mode === 'register' && !isTestnet ? 'stop-btn' : 'btn-yellow'} 
            style={{ 
              width: '100%', 
              marginTop: '30px', 
              height: '50px', 
              background: mode === 'register' && !isTestnet ? '#f44336' : '' 
            }}
            disabled={loading}
          >
            {loading ? 'Procesando...' : mode === 'register' 
              ? (isTestnet ? 'Registrar en Testnet' : 'REGISTRAR EN CUENTA REAL')
              : 'Iniciar Sesión'}
          </button>
        </form>
        
        <div style={{ marginTop: '20px', textAlign: 'center' }}>
          <button
            type="button"
            onClick={() => {
              setMode(mode === 'login' ? 'register' : 'login');
              setError('');
            }}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--binance-yellow)',
              cursor: 'pointer',
              fontSize: '0.9rem',
              textDecoration: 'underline'
            }}
          >
            {mode === 'login' ? '¿No tienes cuenta? Regístrate' : '¿Ya tienes cuenta? Inicia sesión'}
          </button>
        </div>
        
        <div style={{ marginTop: '20px', fontSize: '0.8em', color: '#666', textAlign: 'center' }}>
          {mode === 'register' 
            ? 'Tus API keys se almacenan de forma segura y encriptada.'
            : 'Ingresa con tu username para acceder a tu bot.'}
        </div>
      </div>
    </div>
  );
};

export default Login;
