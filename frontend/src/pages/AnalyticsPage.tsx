import { useEffect, useMemo, useState } from "react";
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
  Info,
  RotateCcw,
  AlertCircle,
  Clock3,
  FileWarning,
  Sparkles,
} from "lucide-react";
import {
  getAnalyticsSummary,
  type AnalyticsSummaryResponse,
} from "@/api/analytics";

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
  const [data, setData] = useState<AnalyticsSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const daysNum = useMemo(() => {
    const parsed = parseInt(range, 10);
    return isNaN(parsed) ? 30 : parsed;
  }, [range]);

  const loadData = async () => {
    setLoading(true);
    setError(false);
    try {
      const summary = await getAnalyticsSummary(daysNum);
      setData(summary);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, [daysNum]);

  // Transform data for charts
  const rulesData = useMemo(() => {
    if (!data?.mostViolatedRules) return [];
    return data.mostViolatedRules.map((r) => ({
      name: r.label,
      count: r.count,
      ruleId: r.ruleId,
    }));
  }, [data]);

  const rejectedSuggestionsData = useMemo(() => {
    if (!data?.mostRejectedSuggestions) return [];
    return data.mostRejectedSuggestions.map((s) => ({
      name: s.label,
      count: s.count,
      type: s.type,
    }));
  }, [data]);

  const issueTrendData = useMemo(() => {
    if (!data?.issuesOverTime) return [];
    return data.issuesOverTime.map((i) => ({
      day: i.date,
      high: i.critical,
      medium: i.warning,
      low: i.info,
    }));
  }, [data]);

  const teamsData = useMemo(() => {
    if (!data?.reviewTimeByTeam) return [];
    return data.reviewTimeByTeam.map((t) => ({
      team: t.team,
      minutes: t.avgMinutes,
    }));
  }, [data]);

  // Determine active KPI cards (only where not null / not hidden)
  const activeKpis = useMemo(() => {
    if (!data) return [];
    const list = [];

    if (data.kpis.avgReviewMinutes != null) {
      list.push({
        label: "Average review time",
        value: `${data.kpis.avgReviewMinutes} min`,
        trend: `${data.kpis.avgReviewItems} items`,
        icon: Clock3,
        tip: "Average time from content submission to a completed review.",
      });
    }

    if (data.kpis.unresolvedIssues > 0) {
      list.push({
        label: "Unresolved issues",
        value: String(data.kpis.unresolvedIssues),
        trend: "open",
        icon: AlertCircle,
        tip: "Issues detected in content that have not yet been resolved.",
      });
    }

    if (data.kpis.outdatedPublishedPosts > 0) {
      list.push({
        label: "Outdated published content",
        value: String(data.kpis.outdatedPublishedPosts),
        trend: "needs review",
        icon: FileWarning,
        tip: "Published items that may need an update because a linked fact or guideline changed.",
      });
    }

    if (data.kpis.suggestionsAcceptedPct != null) {
      list.push({
        label: "AI suggestions accepted",
        value: `${data.kpis.suggestionsAcceptedPct}%`,
        trend: `${data.kpis.decisionCount} decisions`,
        icon: Sparkles,
        tip: "Percentage of AI suggestions that reviewers accepted.",
      });
    }

    return list;
  }, [data]);

  // Check if every card is hidden
  const isAllHidden = useMemo(() => {
    if (!data) return true;
    return (
      activeKpis.length === 0 &&
      rulesData.length === 0 &&
      rejectedSuggestionsData.length === 0 &&
      issueTrendData.length === 0 &&
      teamsData.length === 0
    );
  }, [data, activeKpis, rulesData, rejectedSuggestionsData, issueTrendData, teamsData]);

  return (
    <div className="h-full space-y-4 overflow-y-auto pb-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#14213D]">Analytics</h1>
          <p className="mt-1 text-xs text-slate-500">
            What goes wrong most often, and how the review process is doing
          </p>
          <p className="mt-1 text-[11px] text-slate-400">
            Manager and admin view · {range}
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
            onClick={() => void loadData()}
            className="flex h-9 items-center gap-2 rounded-lg border border-[#E3E8F2] bg-white px-3 text-xs font-medium hover:bg-slate-50"
          >
            <RotateCcw size={14} /> Refresh
          </button>
        </div>
      </header>

      {error && (
        <div
          role="alert"
          className="flex items-center justify-between rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          <div className="flex items-center gap-2">
            <AlertCircle size={17} />
            <span>Analytics could not be loaded. Check your connection and try again.</span>
          </div>
          <button onClick={() => void loadData()} className="font-semibold underline">
            Retry
          </button>
        </div>
      )}

      {loading && (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, idx) => (
              <Skeleton key={idx} className="h-[88px]" />
            ))}
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
        </>
      )}

      {!loading && !error && isAllHidden && (
        <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed border-[#D5DDEB] bg-white p-12 text-center">
          <div className="mb-3 rounded-full bg-slate-100 p-3">
            <FileWarning size={22} className="text-slate-500" />
          </div>
          <h2 className="text-sm font-semibold text-[#14213D]">Not enough data yet</h2>
          <p className="mt-1 max-w-sm text-xs text-slate-500">
            Analytics will appear as your team reviews content and resolves issues.
          </p>
        </div>
      )}

      {!loading && !error && !isAllHidden && (
        <>
          {activeKpis.length > 0 && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {activeKpis.map((kpi) => {
                const Icon = kpi.icon;
                return (
                  <div
                    key={kpi.label}
                    className="flex h-[88px] items-center gap-3 rounded-xl border border-[#E3E8F2] bg-white px-4"
                  >
                    <div className="rounded-lg bg-slate-50 p-2">
                      <Icon size={17} className="text-slate-500" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <p className="truncate text-[11px] text-slate-500">{kpi.label}</p>
                        <InfoTip text={kpi.tip} />
                      </div>
                      <div className="mt-1 flex items-baseline gap-2">
                        <span className="text-xl font-semibold text-[#14213D]">{kpi.value}</span>
                        <span className="inline-flex items-center text-[10px] font-medium text-slate-500">
                          {kpi.trend}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {selectedRule && (
            <div className="flex items-center justify-between rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-900">
              <span>Filtering by <strong>{selectedRule}</strong>.</span>
              <button onClick={() => setSelectedRule("")} className="font-semibold underline">
                Clear filter
              </button>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {rulesData.length > 0 && (
              <ChartCard
                title="Most violated rules"
                takeaway="Common guideline infractions found during check runs."
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={rulesData}
                    layout="vertical"
                    margin={{ top: 2, right: 12, left: 12, bottom: 2 }}
                    onClick={(event: any) => {
                      const name = event?.activePayload?.[0]?.payload?.name;
                      if (name) setSelectedRule((current) => (current === name ? "" : name));
                    }}
                  >
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#EDF1F7" />
                    <XAxis type="number" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="name" width={145} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="count" name="Issues" radius={[0, 4, 4, 0]} cursor="pointer">
                      {rulesData.map((rule) => (
                        <Cell
                          key={rule.name}
                          fill={selectedRule === rule.name ? "#14213D" : "#5276F5"}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            )}

            {rejectedSuggestionsData.length > 0 && (
              <ChartCard
                title="Most rejected suggestions"
                takeaway="AI fix suggestions rejected during review."
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={rejectedSuggestionsData}
                    layout="vertical"
                    margin={{ top: 2, right: 12, left: 12, bottom: 2 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#EDF1F7" />
                    <XAxis type="number" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="name" width={145} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="count" name="Rejected" fill="#E68B70" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            )}

            {issueTrendData.length > 0 && (
              <ChartCard
                title="Issues over time"
                takeaway="Severity breakdown of findings detected by check runs across the selected window."
              >
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={issueTrendData} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#EDF1F7" />
                    <XAxis dataKey="day" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Line type="monotone" dataKey="high" name="Critical" stroke="#D94B4B" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="medium" name="Warning" stroke="#D99A24" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="low" name="Info" stroke="#39866A" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </ChartCard>
            )}

            {teamsData.length > 0 && (
              <ChartCard
                title="Review time by team"
                takeaway="Average duration from submission to approval grouped by content team."
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={teamsData} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#EDF1F7" />
                    <XAxis dataKey="team" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={tooltipStyle} formatter={(value) => [`${value} min`, "Average review time"]} />
                    <Bar dataKey="minutes" name="Minutes" fill="#5276F5" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            )}
          </div>
        </>
      )}
    </div>
  );
}
