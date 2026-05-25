import React, { createContext, useContext } from "react";

// Stub do AuthProvider — o Firebase foi removido. Mantemos a API para compatibilidade
const AuthContext = createContext({
  user: null,
  loginWithGoogle: async () => {},
  logout: async () => {},
});
export const useAuth = () => useContext(AuthContext);

export default function AuthProvider({ children }) {
  return (
    <AuthContext.Provider
      value={{
        user: null,
        loginWithGoogle: async () => {},
        logout: async () => {},
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
