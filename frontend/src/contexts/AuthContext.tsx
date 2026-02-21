import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import api from "@/api/client";

interface AuthState {
  token: string | null;
  user: { sub: string; username: string } | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>(null!);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [user, setUser] = useState<AuthState["user"]>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      api.get("/auth/verify").then((r) => {
        setUser(r.data.user);
        setLoading(false);
      }).catch(() => {
        localStorage.removeItem("token");
        setToken(null);
        setLoading(false);
      });
    } else {
      setLoading(false);
    }
  }, [token]);

  const login = async (username: string, password: string) => {
    const r = await api.post("/auth/login", { username, password });
    localStorage.setItem("token", r.data.access_token);
    setToken(r.data.access_token);
  };

  const register = async (username: string, password: string) => {
    const r = await api.post("/auth/register", { username, password });
    localStorage.setItem("token", r.data.access_token);
    setToken(r.data.access_token);
  };

  const logout = () => {
    api.post("/auth/logout").catch(() => {});
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ token, user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
