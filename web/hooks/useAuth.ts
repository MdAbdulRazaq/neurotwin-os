"use client";
import { createContext, createElement, useContext, useState, useEffect, useCallback, ReactNode } from "react";

interface User { user_id: string; email: string; plan: string; }
interface AuthCtx { user: User|null; token: string; login: (e:string,p:string)=>Promise<void>; logout: ()=>void; identify: (id:string,traits?:any)=>void; }

const Ctx = createContext<AuthCtx>({ user:null, token:"", login:async()=>{}, logout:()=>{}, identify:()=>{} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser]   = useState<User|null>(null);
  const [token, setToken] = useState<string>("");

  useEffect(() => {
    const saved = sessionStorage.getItem("nt_user");
    const savedTok = sessionStorage.getItem("nt_token");
    if (saved && savedTok) { setUser(JSON.parse(saved)); setToken(savedTok); }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const r = await fetch("/api/auth/login", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ email, password }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || "Login failed");
    const data = await r.json();
    setUser({ user_id: data.user_id, email: data.email, plan: data.plan });
    setToken(data.access_token);
    sessionStorage.setItem("nt_user", JSON.stringify({ user_id: data.user_id, email: data.email, plan: data.plan }));
    sessionStorage.setItem("nt_token", data.access_token);
  }, []);

  const logout = useCallback(() => {
    setUser(null); setToken("");
    sessionStorage.removeItem("nt_user"); sessionStorage.removeItem("nt_token");
  }, []);

  const identify = useCallback((id: string, traits: any = {}) => {
    fetch("/api/events", { method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ events:[{ event:"user_identified", user_id:id, properties:traits }] }) }).catch(()=>{});
  }, []);

  return createElement(Ctx.Provider, { value: { user, token, login, logout, identify } }, children);
}

export const useAuth = () => useContext(Ctx);

export function useRequireAuth(redirectTo = "/login") {
  const { user } = useAuth();
  useEffect(() => { if (!user && typeof window !== "undefined") window.location.href = redirectTo; }, [user]);
  return user;
}
