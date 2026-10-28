
import { useMemo, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";
import {
  ArrowDownRight,
  ArrowUpRight,
  Info,
  RotateCcw,
  AlertCircle,
  Clock3,
  FileWarning,
  Sparkles,
  ChevronRight,
} from "lucide-react";

const rules = [
  { name: "Absolute claims", count: 42, rejected: 68, precision: 91, recall: 84, wording: "Avoid claims such as “always” or “guaranteed” unless supported by approved evidence." },
  { name: "Unsupported product claims", count: 34, rejected: 54, precision: 86, recall: 78, wording: "Use only product benefits backed by a current, approved fact." },
  { name: "Outdated pricing", count: 26, rejected: 43, precision: 94, recall: 92, wording: "Verify the current approved price before publishing." },
  { name: "Tone of voice", count: 19, rejected: 31, precision: 82, recall: 73, wording: "Use clear, helpful language instead of exaggerated or aggressive wording." },
  { name: "Missing disclaimer", count: 15, rejected: 24, precision: 96, recall: 89, wording: "Include the required disclaimer wherever this claim appears." },
];

const issueTrend = [
  { day: "Oct 19", high: 12, medium: 21, low: 16 },
  { day: "Oct 20", high: 9, medium: 24, low: 18 },
  { day: "Oct 21", high: 14, medium: 19, low: 14 },
  { day: "Oct 22", high: 7, medium: 17, low: 20 },
  { day: "Oct 23", high: 8, medium: 14, low: 13 },
  { day: "Oct 24", high: 5, medium: 12, low: 11 },
  { day: "Oct 25", high: 4, medium: 10, low: 8 },
];

const teams = [
  { team: "Marketing", minutes: 46 },
  { team: "Product", minutes: 32 },
  { team: "Sales", minutes: 28 },
  { team: "Support", minutes: 21 },
];

const rejectedSuggestions = [
  { name: "Tone rewrite", count: 31 },
  { name: "Claim correction", count: 24 },
  { name: "Suggested disclaimer", count: 18 },
  { name: "Terminology change", count: 12 },
  { name: "Visual suggestion", count: 7 },
];

const tooltipStyle = {
  borderRadius: 10,
  border: "1px solid #E3E8F2",
  fontSize: 12,
};

function InfoTip({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex">
      <Info size={14} className="cursor-help text-slate-400" aria-label={text} />
      <span className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-56 -translate-x-1/2 rounded-lg bg-[#14213D] p-2 text-xs font-normal leading-5 text-white shadow-lg group-hover:block group-focus-within:block">
        {text}
      </span>
    </span>
  );
}

function ChartCard({
  title,
  takeaway,
  children,
  action,
}: {
  title: string;
  takeaway: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className="min-w-0 rounded-xl border border-[#E3E8F2] bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-[#14213D]">{title}</h2>
          <p className="mt-1 text-xs leading-5 text-slate-500">{takeaway}</p>
        </div>
        {action}
      </div>
      <div className="mt-4 h-[220px] w-full">{children}</div>
    </section>
  );
}

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-slate-100 ${className}`} />;
}

export default function AnalyticsPage() {
  const [range, setRange] = useState("30 days");
  const [selectedRule, setSelectedRule] = useState("");
  const [state, setState] = useState<"ready" | "loading" | "empty" | "error">("ready");

  const visibleRules = useMemo(
    () => selectedRule ? rules.filter((rule) => rule.name === selectedRule) : rules,
    [selectedRule],
  );

  const kpis = [
    {
      label: "Average review time",
      value: range === "7 days" ? "24 min" : range === "90 days" ? "31 min" : "28 min",
      trend: "12% faster",
      positive: true,
      icon: Clock3,
      tip: "Average time from content submission to a completed review.",
    },
    {
      label: "Unresolved issues",
      value: range === "7 days" ? "18" : range === "90 days" ? "64" : "32",
      trend: "8% higher",
      positive: false,
      icon: AlertCircle,
      tip: "Issues detected in the selected period that have not been resolved.",
    },
    {
      label: "Outdated published content",
      value: range === "7 days" ? "6" : range === "90 days" ? "29" : "14",
      trend: "3 fewer",
      positive: true,
      icon: FileWarning,
      tip: "Published items that may need an update because a linked fact or guideline changed.",
    },
    {
      label: "AI suggestions accepted",
      value: range === "7 days" ? "74%" : range === "90 days" ? "69%" : "72%",
      trend: "5% higher",
      positive: true,
      icon: Sparkles,
      tip: "Percentage of AI suggestions that reviewers accepted, fully or in part.",
    },
  ];

  const resetDemo = () => {
    setSelectedRule("");
    setState("ready");
  };

  return (
    <div className="h-full space-y-4 overflow-y-auto pb-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#14213D]">Analytics</h1>
          <p className="mt-1 text-xs text-slate-500">
            What goes wrong most often, and how the review process is doing
          </p>
          <p className="mt-1 text-[11px] text-slate-400">
            Manager and admin view · {range} · Illustrative demo data
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Analytics date range"
            value={range}
            onChange={(event) => setRange(event.target.value)}
            className="h-9 rounded-lg border border-[#E3E8F2] bg-white px-3 text-xs text-slate-700 outline-none focus:ring-2 focus:ring-blue-200"
          >
            <option>7 days</option>
            <option>30 days</option>
            <option>90 days</option>
          </select>
          <button
            onClick={() => setState("loading")}
            className="flex h-9 items-center gap-2 rounded-lg border border-[#E3E8F2] bg-white px-3 text-xs font-medium hover:bg-slate-50"
          >
            <RotateCcw size={14} /> Refresh
          </button>
          <div className="flex gap-1 rounded-lg border border-[#E3E8F2] bg-white p-1">
            {(["ready", "loading", "empty", "error"] as const).map((item) => (
              <button
                key={item}
                onClick={() => setState(item)}
                className={`rounded-md px-2 py-1 text-[10px] capitalize ${
                  state === item ? "bg-[#14213D] text-white" : "text-slate-500 hover:bg-slate-100"
                }`}
                aria-label={`Show ${item} state`}
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      </header>

      {state === "error" && (
        <div role="alert" className="flex items-center justify-between rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <div className="flex items-center gap-2">
            <AlertCircle size={17} />
            <span>Analytics could not be loaded. Check your connection and try again.</span>
          </div>
          <button onClick={resetDemo} className="font-semibold underline">Retry</button>
        </div>
      )}

      {state === "empty" && (
        <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed border-[#D5DDEB] bg-white text-center">
          <div className="mb-3 rounded-full bg-slate-100 p-3"><FileWarning size={22} className="text-slate-500" /></div>
          <h2 className="text-sm font-semibold text-[#14213D]">Not enough data yet</h2>
          <p className="mt-1 max-w-sm text-xs text-slate-500">
            Analytics will appear as your team reviews content and resolves issues.
          </p>
          <button onClick={resetDemo} className="mt-4 rounded-lg bg-[#2F5BEA] px-4 py-2 text-xs font-semibold text-white">
            Show demo data
          </button>
        </div>
      )}

      {state === "loading" && (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {kpis.map((kpi) => <Skeleton key={kpi.label} className="h-[88px]" />)}
          </div>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="rounded-xl border border-[#E3E8F2] bg-white p-4">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="mt-2 h-3 w-56" />
                <Skeleton className="mt-5 h-[220px] w-full" />
              </div>
            ))}
          </div>
          <button onClick={() => setState("ready")} className="text-xs font-medium text-blue-700 underline">
            Finish loading demo data
          </button>
        </>
      )}

      {state === "ready" && (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {kpis.map((kpi) => {
              const Icon = kpi.icon;
              return (
                <div key={kpi.label} className="flex h-[88px] items-center gap-3 rounded-xl border border-[#E3E8F2] bg-white px-4">
                  <div className="rounded-lg bg-slate-50 p-2"><Icon size={17} className="text-slate-500" /></div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <p className="truncate text-[11px] text-slate-500">{kpi.label}</p>
                      <InfoTip text={kpi.tip} />
                    </div>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-xl font-semibold text-[#14213D]">{kpi.value}</span>
                      <span className={`inline-flex items-center text-[10px] font-medium ${kpi.positive ? "text-emerald-700" : "text-amber-700"}`}>
                        {kpi.positive ? <ArrowDownRight size={12} /> : <ArrowUpRight size={12} />}
                        {kpi.trend}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {selectedRule && (
            <div className="flex items-center justify-between rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-900">
              <span>Filtering rule recommendations by <strong>{selectedRule}</strong>.</span>
              <button onClick={() => setSelectedRule("")} className="font-semibold underline">Clear filter</button>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <ChartCard
              title="Most violated rules"
              takeaway="Absolute claims are the most common mistake. Select a bar to filter rule recommendations."
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rules} layout="vertical" margin={{ top: 2, right: 12, left: 12, bottom: 2 }} onClick={(event: any) => {
                  const name = event?.activePayload?.[0]?.payload?.name;
                  if (name) setSelectedRule((current) => current === name ? "" : name);
                }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#EDF1F7" />
                  <XAxis type="number" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="name" width={145} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="count" name="Issues" radius={[0, 4, 4, 0]} cursor="pointer">
                    {rules.map((rule) => (
                      <Cell key={rule.name} fill={selectedRule === rule.name ? "#14213D" : "#5276F5"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard
              title="Most rejected suggestions"
              takeaway="Tone rewrites are rejected most often, suggesting reviewers prefer to preserve their original voice."
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rejectedSuggestions} layout="vertical" margin={{ top: 2, right: 12, left: 12, bottom: 2 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#EDF1F7" />
                  <XAxis type="number" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="name" width={145} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="count" name="Rejected" fill="#E68B70" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard
              title="Issues over time"
              takeaway="High-severity issues are trending down across the selected sample period."
            >
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={issueTrend} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#EDF1F7" />
                  <XAxis dataKey="day" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Line type="monotone" dataKey="high" name="High severity" stroke="#D94B4B" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="medium" name="Medium severity" stroke="#D99A24" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="low" name="Low severity" stroke="#39866A" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard
              title="Review time by team"
              takeaway="Marketing takes the longest on average, so its review workflow may need attention."
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={teams} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#EDF1F7" />
                  <XAxis dataKey="team" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(value) => [`${value} min`, "Average review time"]} />
                  <Bar dataKey="minutes" name="Minutes" fill="#5276F5" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.4fr_1fr]">
            <section className="rounded-xl border border-[#E3E8F2] bg-white p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-[#14213D]">Rules to clarify</h2>
                  <p className="mt-1 text-xs text-slate-500">High rejection rates may mean a rule needs clearer examples.</p>
                </div>
                <span className="rounded-full bg-amber-50 px-2 py-1 text-[10px] font-medium text-amber-800">Needs attention</span>
              </div>
              <div className="mt-3 divide-y divide-slate-100">
                {visibleRules.map((rule) => (
                  <div key={rule.name} className="py-3 first:pt-1 last:pb-0">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-xs font-semibold text-[#14213D]">{rule.name}</div>
                      <span className="text-[11px] font-medium text-amber-700">{rule.rejected}% rejected</span>
                    </div>
                    <p className="mt-1 text-xs leading-5 text-slate-600">{rule.wording}</p>
                    <button
                      onClick={() => window.alert(`Open rule editor for: ${rule.name}`)}
                      className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-[#2F5BEA] hover:underline"
                    >
                      Review rule <ChevronRight size={13} />
                    </button>
                  </div>
                ))}
                {visibleRules.length === 0 && <p className="py-4 text-xs text-slate-500">No rules match this filter.</p>}
              </div>
            </section>

            <section className="rounded-xl border border-[#E3E8F2] bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-sm font-semibold text-[#14213D]">AI quality</h2>
                  <p className="mt-1 text-xs leading-5 text-slate-500">How reliably the AI identifies issues and avoids false alarms.</p>
                </div>
                <InfoTip text="Precision means: when AI flags something, how often is it actually an issue? Recall means: of all real issues, how many did AI find?" />
              </div>
              <div className="mt-4 space-y-4">
                {rules.slice(0, 4).map((rule) => (
                  <div key={rule.name}>
                    <p className="mb-2 text-xs font-medium text-slate-700">{rule.name}</p>
                    {([
                      ["Precision", rule.precision, "#2F5BEA"],
                      ["Recall", rule.recall, "#3A9272"],
                    ] as const).map(([label, value, color]) => (
                      <div key={label} className="mb-2 flex items-center gap-2">
                        <span className="w-[62px] text-[10px] text-slate-500">{label}</span>
                        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                          <div className="h-full rounded-full" style={{ width: `${value}%`, backgroundColor: color }} />
                        </div>
                        <span className="w-8 text-right text-[10px] font-semibold text-slate-700">{value}%</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </section>
          </div>

          <p className="text-[10px] text-slate-400">
            Demo note: connect these components to your analytics API before using the metrics for business decisions.
          </p>
        </>
      )}
    </div>
  );
}
