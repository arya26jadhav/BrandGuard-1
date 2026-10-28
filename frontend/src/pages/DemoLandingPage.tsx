
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ShieldCheck,
  Search,
  Link2,
  BellRing,
  ArrowRight,
  RotateCcw,
  Check,
  Sparkles,
  FileCheck2,
  X,
} from "lucide-react";

type DemoRole = "creator" | "sales-creator" | "manager" | "reviewer" | "admin";

type Persona = {
  id: DemoRole;
  name: string;
  role: string;
  description: string;
  initials: string;
  color: string;
  tag?: string;
  route: string;
};

const personas: Persona[] = [
  {
    id: "creator",
    name: "Maya Chen",
    role: "Creator",
    description: "Draft content, check brand issues, and submit for approval.",
    initials: "MC",
    color: "bg-blue-100 text-blue-700",
    tag: "Recommended start",
    route: "/content",
  },
  {
    id: "sales-creator",
    name: "Rahul Mehta",
    role: "Creator · Sales",
    description: "Prepare sales content and check product claims before sharing.",
    initials: "RM",
    color: "bg-emerald-100 text-emerald-700",
    route: "/content",
  },
  {
    id: "manager",
    name: "Priya Sharma",
    role: "Brand Manager",
    description: "Review submissions, manage brand rules, and track analytics.",
    initials: "PS",
    color: "bg-violet-100 text-violet-700",
    route: "/review-queue",
  },
  {
    id: "reviewer",
    name: "Rohan Mehta",
    role: "Reviewer",
    description: "Inspect flagged issues, request changes, and approve content.",
    initials: "RM",
    color: "bg-amber-100 text-amber-800",
    route: "/review-queue",
  },
  {
    id: "admin",
    name: "Admin user",
    role: "Administrator",
    description: "Explore the governance setup, users, rules, and demo workspace.",
    initials: "AD",
    color: "bg-slate-200 text-slate-700",
    route: "/guidelines",
  },
];

const features = [
  {
    icon: Search,
    title: "Find issues before publishing",
    description: "Check content before it goes live.",
  },
  {
    icon: Link2,
    title: "Every flag shows its source",
    description: "Trace findings back to approved facts and rules.",
  },
  {
    icon: BellRing,
    title: "Alerts only reach the right owners",
    description: "Notify the people who can resolve an issue.",
  },
];

const steps = [
  { number: "01", title: "Choose a role", detail: "Explore the app as a team member." },
  { number: "02", title: "Open content", detail: "Start with a sample draft." },
  { number: "03", title: "Review findings", detail: "See flags and their sources." },
  { number: "04", title: "Fix and approve", detail: "Try the review workflow." },
];

export default function DemoLandingPage() {
  const navigate = useNavigate();
  const [resetOpen, setResetOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<DemoRole>("creator");
  const [continuing, setContinuing] = useState(false);

  function continueAs(persona: Persona) {
    setSelectedRole(persona.id);
    setContinuing(true);

    // Persist the demo identity for the workspace to read.
    sessionStorage.setItem("brandguard-demo-persona", persona.id);
    sessionStorage.setItem("brandguard-demo-name", persona.name);
    sessionStorage.setItem("brandguard-demo-role", persona.role);

    // Keep the existing app shell and open the selected role's home page.
    navigate(persona.route);
  }

  function resetDemo() {
    sessionStorage.removeItem("brandguard-demo-persona");
    sessionStorage.removeItem("brandguard-demo-name");
    sessionStorage.removeItem("brandguard-demo-role");

    // Clear only BrandGuard demo-specific local state.
    localStorage.removeItem("brandguard-demo-data");
    localStorage.removeItem("brandguard-content-demo");

    setResetOpen(false);
    setContinuing(false);
    setSelectedRole("creator");
    navigate("/");
  }

  return (
    <div className="min-h-screen bg-[#F6F8FC] px-4 py-8 text-[#1F2937] sm:py-12">
      <main className="mx-auto w-full max-w-[960px]">
        <header className="flex flex-col items-center text-center">
          <div className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#14213D] text-white shadow-sm">
              <ShieldCheck size={23} strokeWidth={2.2} />
            </div>
            <span className="text-xl font-bold tracking-tight text-[#14213D]">
              BrandGuard
            </span>
          </div>

          <div className="mt-8 inline-flex items-center gap-1.5 rounded-full border border-blue-100 bg-white px-3 py-1.5 text-[11px] font-medium text-[#2F5BEA]">
            <Sparkles size={13} />
            Interactive product demo
          </div>

          <h1 className="mt-4 max-w-[760px] text-3xl font-semibold leading-tight tracking-tight text-[#14213D] sm:text-4xl">
            Check your content against your brand rules before it goes live
          </h1>

          <p className="mt-4 max-w-[740px] text-sm leading-6 text-slate-600 sm:text-base sm:leading-7">
            Catch unsupported claims, wrong terms and off-brand visuals, see
            exactly why, fix them in one click, and get human approval.
          </p>
        </header>

        <section className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3" aria-label="BrandGuard benefits">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className="flex items-start gap-3 rounded-xl border border-[#E3E8F2] bg-white p-3.5"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-[#2F5BEA]">
                  <Icon size={17} />
                </div>
                <div>
                  <h2 className="text-xs font-semibold text-[#14213D]">
                    {feature.title}
                  </h2>
                  <p className="mt-1 text-[11px] leading-4 text-slate-500">
                    {feature.description}
                  </p>
                </div>
              </div>
            );
          })}
        </section>

        <section className="mt-9">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold text-[#14213D]">
                Choose a demo role
              </h2>
              <p className="mt-1 text-xs text-slate-500">
                Each role has a different view of the brand review workflow.
              </p>
            </div>
            <span className="text-[11px] text-slate-400">
              No account or password needed
            </span>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            {personas.map((persona) => {
              const isSelected = selectedRole === persona.id;

              return (
                <article
                  key={persona.id}
                  className={`relative flex flex-col rounded-xl border bg-white p-4 transition-all ${
                    isSelected
                      ? "border-[#2F5BEA] ring-1 ring-blue-100"
                      : "border-[#E3E8F2] hover:border-slate-300 hover:shadow-sm"
                  }`}
                >
                  {persona.tag && (
                    <span className="absolute right-3 top-3 inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-1 text-[10px] font-semibold text-[#2F5BEA]">
                      <Sparkles size={11} />
                      {persona.tag}
                    </span>
                  )}

                  <div className="flex items-start gap-3">
                    <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-xs font-bold ${persona.color}`}>
                      {persona.initials}
                    </div>
                    <div className="min-w-0 flex-1 pr-1">
                      <h3 className="text-sm font-semibold text-[#14213D]">
                        {persona.name}
                      </h3>
                      <p className="mt-0.5 text-xs font-medium text-slate-500">
                        {persona.role}
                      </p>
                      <p className="mt-2 text-xs leading-5 text-slate-600">
                        {persona.description}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center justify-between gap-3 border-t border-slate-100 pt-3">
                    <span className="inline-flex items-center gap-1.5 text-[10px] text-slate-400">
                      <Check size={12} />
                      Sample workspace
                    </span>
                    <button
                      onClick={() => continueAs(persona)}
                      disabled={continuing}
                      className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-[#2F5BEA] px-3.5 text-xs font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-wait disabled:opacity-70"
                    >
                      Continue as
                      <ArrowRight size={14} />
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="mt-8 rounded-xl border border-[#E3E8F2] bg-white p-4 sm:p-5">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
              <FileCheck2 size={16} />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-[#14213D]">
                How to try it in 3 minutes
              </h2>
              <p className="mt-0.5 text-[11px] text-slate-500">
                Follow this quick path to see the core workflow.
              </p>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {steps.map((step) => (
              <div key={step.number} className="flex items-start gap-2.5">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#14213D] text-[10px] font-semibold text-white">
                  {step.number}
                </span>
                <div>
                  <p className="text-xs font-semibold text-[#14213D]">
                    {step.title}
                  </p>
                  <p className="mt-1 text-[11px] leading-4 text-slate-500">
                    {step.detail}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <p className="text-[11px] text-slate-400">
            Demo environment - sample data for a fictional brand, GreenGlow.
          </p>
          <button
            onClick={() => setResetOpen(true)}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 underline decoration-slate-300 underline-offset-4 hover:text-red-700"
          >
            <RotateCcw size={12} />
            Reset demo data
          </button>
        </div>
      </main>

      {resetOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setResetOpen(false);
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="reset-title"
            className="w-full max-w-sm rounded-xl border border-[#E3E8F2] bg-white p-5 shadow-xl"
          >
            <div className="flex items-start justify-between">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-red-50 text-red-600">
                <RotateCcw size={17} />
              </div>
              <button
                onClick={() => setResetOpen(false)}
                aria-label="Close reset confirmation"
                className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100"
              >
                <X size={16} />
              </button>
            </div>

            <h2 id="reset-title" className="mt-4 text-base font-semibold text-[#14213D]">
              Reset demo data?
            </h2>
            <p className="mt-2 text-xs leading-5 text-slate-600">
              This clears the demo-specific session and local data keys from
              this browser. Any data stored by a connected backend must be
              reset separately.
            </p>

            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => setResetOpen(false)}
                className="h-9 rounded-lg border border-[#E3E8F2] px-3 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={resetDemo}
                className="h-9 rounded-lg bg-red-600 px-3 text-xs font-semibold text-white hover:bg-red-700"
              >
                Reset demo
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
