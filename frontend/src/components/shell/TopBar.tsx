import { useEffect, useMemo, useState } from "react";
import { Bell, Check, ChevronDown, Command, Menu, Search, ShieldCheck, X } from "lucide-react";
import { api, apiRequest, setToken } from "@/api/client";
import type { DemoUser } from "@/types";
import { OnboardingBanner } from "@/components/shell/OnboardingBanner";

type TopBarProps = { user: DemoUser; onUserChange: (user: DemoUser) => void; onMenuClick: () => void; onNavigate: (path: string) => void };
export function TopBar({ user, onUserChange, onMenuClick, onNavigate }: TopBarProps) {
  const [roleOpen, setRoleOpen] = useState(false);
  const [demoUsers, setDemoUsers] = useState<DemoUser[]>([]);
  // The demo switcher is for local demos only. The real user always comes from /api/auth/me.
  const showSwitcher = import.meta.env.VITE_SHOW_DEMO_SWITCHER === "true";

  useEffect(() => {
    if (!showSwitcher || !roleOpen) return;
    apiRequest<DemoUser[]>("/api/auth/demo-users")
      .then(setDemoUsers)
      .catch(() => setDemoUsers([]));
  }, [showSwitcher, roleOpen]);
  const [searchOpen, setSearchOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [searchValue, setSearchValue] = useState("");
  const selectedUser = useMemo(() => demoUsers.find((item) => item.role === user.role) ?? user, [user]);

  const switchRole = async (demoUser: DemoUser) => {
    try {
      const response = await api.loginAs(demoUser.id);
      setToken(response.token);
      onUserChange(response.user);
    } catch (error) {
      console.error("Could not switch BrandGuard demo user:", error);
    } finally {
      setRoleOpen(false);
    }
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
        window.setTimeout(() => document.getElementById("brandguard-global-search")?.focus(), 0);
      }
      if (event.key === "Escape") { setRoleOpen(false); setNotificationsOpen(false); setSearchOpen(false); }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return <header className="sticky top-0 z-40 flex h-14 items-center justify-between gap-3 border-b border-white/10 bg-[#102B4E] px-3 text-white shadow-sm sm:px-5">
    <div className="flex min-w-0 items-center gap-3">
      <button type="button" onClick={onMenuClick} className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-200 hover:bg-white/10 md:hidden" aria-label="Open navigation menu"><Menu size={19} /></button>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[#57A4FF]"><ShieldCheck size={29} strokeWidth={2.5} aria-hidden="true" /></div>
      <span className="whitespace-nowrap text-[19px] font-bold tracking-tight">BrandGuard</span>
      <span className="hidden h-7 w-px bg-white/25 sm:block" />
      <span className="hidden whitespace-nowrap text-[12px] text-slate-200 md:block">Trusted Content. Stronger Brands.</span>
    </div>

    <div className="flex min-w-0 items-center gap-2 sm:gap-3">
      <div className="relative hidden lg:block">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" size={15} />
        <input id="brandguard-global-search" value={searchValue} onChange={(event) => setSearchValue(event.target.value)} aria-label="Search BrandGuard" placeholder="Search content…" className="h-9 w-48 rounded-md border border-white/15 bg-white/10 pl-8 pr-14 text-[12px] text-white outline-none placeholder:text-slate-300 focus:border-blue-300 focus:ring-2 focus:ring-blue-400/30 xl:w-60" />
        <kbd className="absolute right-2 top-1/2 -translate-y-1/2 rounded border border-white/20 px-1.5 py-0.5 text-[10px] text-slate-200"><Command size={9} className="mr-0.5 inline" /> K</kbd>
      </div>
      <div className="relative lg:hidden">
        <button type="button" onClick={() => setSearchOpen((value) => !value)} className="focus-ring flex h-8 w-8 items-center justify-center rounded-md text-slate-200 hover:bg-white/10" aria-label="Search"><Search size={17} /></button>
        {searchOpen && <div className="absolute right-0 top-10 z-50 w-[min(320px,90vw)] rounded-lg border border-slate-200 bg-white p-2.5 shadow-xl"><div className="relative"><Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" size={15} /><input autoFocus value={searchValue} onChange={(event) => setSearchValue(event.target.value)} id="brandguard-global-search-mobile" aria-label="Search BrandGuard" placeholder="Search content, facts, sources…" className="h-9 w-full rounded-md border border-slate-200 pl-8 pr-8 text-[13px] text-slate-800 outline-none focus:border-brand" /><button onClick={() => setSearchOpen(false)} aria-label="Close search" className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400"><X size={14} /></button></div></div>}
      </div>
      <OnboardingBanner onNavigate={onNavigate} />
      <div className="relative">
        <button type="button" onClick={() => setNotificationsOpen((value) => !value)} className="focus-ring relative flex h-8 w-8 items-center justify-center rounded-md text-slate-200 hover:bg-white/10" aria-label="Notifications, 2 unread"><Bell size={18} /><span className="absolute right-1 top-1 flex h-2.5 w-2.5 rounded-full border border-[#102B4E] bg-[#FF5B64]" /></button>
        {notificationsOpen && <div className="absolute right-0 top-10 z-50 w-72 rounded-lg border border-slate-200 bg-white p-2.5 text-slate-800 shadow-xl"><div className="mb-1 flex items-center justify-between px-1"><p className="text-[13px] font-semibold">Notifications <span className="ml-1 rounded-full bg-red-50 px-1.5 py-0.5 text-[10px] text-red-600">2</span></p><button className="rounded p-1 text-slate-500 hover:bg-slate-100" aria-label="Close notifications" onClick={() => setNotificationsOpen(false)}><X size={14} /></button></div><div className="rounded-md p-2 hover:bg-slate-50"><p className="text-[12px] font-medium">Sunscreen price changed</p><p className="mt-1 text-[11px] leading-4 text-slate-500">3 content items may still show ₹349.</p></div><div className="rounded-md p-2 hover:bg-slate-50"><p className="text-[12px] font-medium">Review requested</p><p className="mt-1 text-[11px] leading-4 text-slate-500">Tea Tree Face Wash — launch post.</p></div></div>}
      </div>
      <div className="relative">
        <button type="button" onClick={() => { if (showSwitcher) setRoleOpen((value) => !value); }} className="focus-ring flex h-9 items-center gap-2 rounded-md px-1.5 text-left hover:bg-white/10" aria-haspopup="listbox" aria-expanded={roleOpen} aria-label={`Current demo user ${user.name}, role ${user.role}. Switch user`}>
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#39A6ED] text-[10px] font-bold text-white">{user.initials}</span>
          <span className="hidden min-w-0 sm:block"><span className="block max-w-28 truncate text-[11px] font-semibold leading-4">{user.name}</span><span className="block text-[10px] capitalize leading-3 text-slate-300">{user.title}</span></span><ChevronDown size={14} className="text-slate-300" />
        </button>
        {showSwitcher && roleOpen && <div role="listbox" aria-label="Switch demo role" className="absolute right-0 top-11 z-50 w-60 rounded-lg border border-slate-200 bg-white p-1.5 text-slate-800 shadow-xl"><div className="px-2 pb-1.5 pt-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">Switch demo role</div>{demoUsers.map((demoUser) => <button key={demoUser.id} role="option" aria-selected={selectedUser.role === demoUser.role} type="button" onClick={() => { void switchRole(demoUser); }} className="focus-ring flex h-10 w-full items-center gap-2.5 rounded-md px-2 text-left hover:bg-slate-50"><span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold text-slate-700">{demoUser.initials}</span><span className="min-w-0 flex-1"><span className="block text-[12px] font-semibold">{demoUser.name}</span><span className="block text-[10px] text-slate-500">{demoUser.title}</span></span>{selectedUser.role === demoUser.role && <Check size={14} className="text-brand" />}</button>)}</div>}
      </div>
    </div>
  </header>;
}
