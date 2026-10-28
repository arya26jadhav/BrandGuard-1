import { useEffect, useState } from "react";
import { Check, CheckCircle2, Circle, ClipboardCheck, X } from "lucide-react";
import { cn } from "@/lib/utils";

type OnboardingBannerProps = { onNavigate: (path: string) => void };
const steps = [
  { label: "Load the sample draft", detail: "Open a draft to review", path: "/content" },
  { label: "Run the check", detail: "Review source-backed findings", path: "/content" },
  { label: "Fix and submit", detail: "Apply a suggestion and submit", path: "/content" },
  { label: "Switch to Reviewer", detail: "Try the approval workflow", path: "/review-queue" },
];
export function OnboardingBanner({ onNavigate }: OnboardingBannerProps) {
  const [visible, setVisible] = useState(true);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const dismissed = window.localStorage.getItem("brandguard-onboarding-dismissed") === "true";
    const seen = window.localStorage.getItem("brandguard-onboarding-seen") === "true";
    setVisible(!dismissed);
    setOpen(!dismissed && !seen);
    if (!dismissed && !seen) window.localStorage.setItem("brandguard-onboarding-seen", "true");
  }, []);
  if (!visible) return null;
  return <div className="relative z-50 flex h-7 items-center">
    <button type="button" className="inline-flex h-6 items-center gap-1.5 whitespace-nowrap rounded-full border border-white/20 bg-white/10 px-2.5 text-[10px] font-semibold text-white hover:bg-white/15" onClick={() => setOpen((value) => !value)} aria-expanded={open}><ClipboardCheck size={12} />Get started <b className="rounded-full bg-white/15 px-1.5 py-0.5 font-semibold">1/4</b></button>
    {open && <div className="absolute right-0 top-9 z-[70] w-[290px] rounded-xl border border-[#E3E8F2] bg-white p-3 text-slate-800 shadow-xl"><div className="flex justify-between gap-3 border-b border-slate-100 pb-2"><div><strong className="text-[12px]">Get started with BrandGuard</strong><p className="mt-0.5 text-[11px] text-slate-500">Four quick steps to explore the demo.</p></div><button type="button" onClick={() => { setOpen(false); setVisible(false); window.localStorage.setItem("brandguard-onboarding-dismissed", "true"); }} aria-label="Dismiss checklist" className="self-start rounded p-0.5 text-slate-500 hover:bg-slate-100"><X size={14} /></button></div>{steps.map((step, index) => <button type="button" key={step.label} className="flex w-full items-center gap-2.5 rounded-md px-1 py-2 text-left hover:bg-slate-50" onClick={() => { onNavigate(step.path); setOpen(false); }}><span className={cn("flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border", index === 0 ? "border-brand bg-brand text-white" : "border-slate-300 text-slate-400")}>{index === 0 ? <Check size={11} /> : <Circle size={10} />}</span><span className="min-w-0 flex-1"><strong className="block text-[11px] font-semibold">{step.label}</strong><small className="mt-0.5 block text-[10px] text-slate-500">{step.detail}</small></span>{index === 0 && <CheckCircle2 size={13} className="text-emerald-600" />}</button>)}</div>}
  </div>;
}
