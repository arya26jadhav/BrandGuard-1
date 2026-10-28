
import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Bell,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock3,
  FileText,
  Filter,
  History,
  Info,
  Plus,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  listFacts,
  updateFact,
  createFact,
  getFactHistory,
  type FactRecord,
} from "@/api/knowledge";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";

type FactStatus = "Active" | "Expiring soon" | "Expired";

type FactHistory = {
  version: number;
  date: string;
  owner: string;
  note: string;
  value: string;
};

type Fact = {
  id: string;
  fact: string;
  value: string;
  product: string;
  owner: string;
  initials: string;
  avatarColor: string;
  version: number;
  expiryDate: string;
  status: FactStatus;
  history: FactHistory[];
};

type ImpactItem = {
  id: string;
  title: string;
  channel: string;
  owner: string;
  initials: string;
  avatarColor: string;
  currentText: string;
  suggestedText: string;
};

const initialFacts: Fact[] = [
  {
    id: "FACT-009",
    fact: "Tea Tree cleanser removes excess oil",
    value: "helps remove excess oil",
    product: "Tea Tree Cleanser",
    owner: "Ananya Sharma",
    initials: "AS",
    avatarColor: "bg-violet-100 text-violet-700",
    version: 3,
    expiryDate: "2026-11-18",
    status: "Active",
    history: [
      {
        version: 3,
        date: "18 Oct 2026",
        owner: "Ananya Sharma",
        note: "Clarified the approved product benefit.",
        value: "helps remove excess oil",
      },
      {
        version: 2,
        date: "02 Oct 2026",
        owner: "Rohan Mehta",
        note: "Updated after product review.",
        value: "removes excess oil",
      },
      {
        version: 1,
        date: "15 Sep 2026",
        owner: "Ananya Sharma",
        note: "Initial fact approved.",
        value: "cleanses oily skin",
      },
    ],
  },
  {
    id: "FACT-014",
    fact: "Daily moisturiser hydration claim",
    value: "provides hydration for up to 24 hours",
    product: "Daily Moisturiser",
    owner: "Rohan Mehta",
    initials: "RM",
    avatarColor: "bg-sky-100 text-sky-700",
    version: 2,
    expiryDate: "2026-11-04",
    status: "Expiring soon",
    history: [
      {
        version: 2,
        date: "10 Oct 2026",
        owner: "Rohan Mehta",
        note: "Approved claim wording updated.",
        value: "provides hydration for up to 24 hours",
      },
      {
        version: 1,
        date: "22 Sep 2026",
        owner: "Rohan Mehta",
        note: "Initial product claim.",
        value: "keeps skin hydrated",
      },
    ],
  },
  {
    id: "FACT-027",
    fact: "Sunscreen SPF rating",
    value: "SPF 50 PA++++",
    product: "Daily Sunscreen",
    owner: "Priya Desai",
    initials: "PD",
    avatarColor: "bg-rose-100 text-rose-700",
    version: 3,
    expiryDate: "2026-10-20",
    status: "Expired",
    history: [
      {
        version: 3,
        date: "20 Sep 2026",
        owner: "Priya Desai",
        note: "Expiry date reached; verification required.",
        value: "SPF 50 PA++++",
      },
      {
        version: 2,
        date: "11 Aug 2026",
        owner: "Priya Desai",
        note: "Updated product label reference.",
        value: "SPF 50",
      },
    ],
  },
  {
    id: "FACT-031",
    fact: "Fragrance-free product statement",
    value: "formulated without added fragrance",
    product: "Sensitive Skin Cream",
    owner: "Ananya Sharma",
    initials: "AS",
    avatarColor: "bg-violet-100 text-violet-700",
    version: 1,
    expiryDate: "2027-02-15",
    status: "Active",
    history: [
      {
        version: 1,
        date: "12 Oct 2026",
        owner: "Ananya Sharma",
        note: "Initial fact approved.",
        value: "formulated without added fragrance",
      },
    ],
  },
  {
    id: "FACT-034",
    fact: "Tea Tree cleanser usage",
    value: "suitable for daily cleansing",
    product: "Tea Tree Cleanser",
    owner: "Rohan Mehta",
    initials: "RM",
    avatarColor: "bg-sky-100 text-sky-700",
    version: 2,
    expiryDate: "2027-01-12",
    status: "Active",
    history: [
      {
        version: 2,
        date: "16 Oct 2026",
        owner: "Rohan Mehta",
        note: "Clarified daily-use wording.",
        value: "suitable for daily cleansing",
      },
    ],
  },
  {
    id: "FACT-038",
    fact: "Packaging recyclability statement",
    value: "check local recycling availability",
    product: "Brand Packaging",
    owner: "Priya Desai",
    initials: "PD",
    avatarColor: "bg-rose-100 text-rose-700",
    version: 1,
    expiryDate: "2027-03-01",
    status: "Active",
    history: [
      {
        version: 1,
        date: "17 Oct 2026",
        owner: "Priya Desai",
        note: "Initial statement approved.",
        value: "check local recycling availability",
      },
    ],
  },
];

const initialImpactItems: ImpactItem[] = [
  {
    id: "GG-104",
    title: "Tea Tree product page",
    channel: "Website",
    owner: "Rohan Mehta",
    initials: "RM",
    avatarColor: "bg-sky-100 text-sky-700",
    currentText:
      "Our Tea Tree cleanser removes excess oil and keeps your skin fresh.",
    suggestedText:
      "Our Tea Tree cleanser helps remove excess oil and keeps your skin fresh.",
  },
  {
    id: "GG-106",
    title: "Face wash campaign",
    channel: "Paid ad",
    owner: "Ananya Sharma",
    initials: "AS",
    avatarColor: "bg-violet-100 text-violet-700",
    currentText:
      "Remove excess oil with our Tea Tree cleanser for a fresh daily routine.",
    suggestedText:
      "Help remove excess oil with our Tea Tree cleanser for a fresh daily routine.",
  },
  {
    id: "GG-111",
    title: "Tea Tree social post",
    channel: "Instagram",
    owner: "Rohan Mehta",
    initials: "RM",
    avatarColor: "bg-sky-100 text-sky-700",
    currentText:
      "Our cleanser removes excess oil, leaving skin feeling clean.",
    suggestedText:
      "Our cleanser helps remove excess oil, leaving skin feeling clean.",
  },
];

const statusStyles: Record<FactStatus, string> = {
  Active: "bg-emerald-50 text-emerald-800 border-emerald-200",
  "Expiring soon": "bg-amber-50 text-amber-900 border-amber-200",
  Expired: "bg-red-50 text-red-800 border-red-200",
};

function getFactStatus(expiryDate: string): FactStatus {
  const expiry = new Date(`${expiryDate}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const days = Math.ceil(
    (expiry.getTime() - today.getTime()) / 86_400_000,
  );

  if (days < 0) return "Expired";
  if (days < 30) return "Expiring soon";
  return "Active";
}

function formatDate(date: string) {
  const parsed = new Date(`${date}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return date;

  return parsed.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function Avatar({
  initials,
  color,
}: {
  initials: string;
  color: string;
}) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[10px] font-bold",
        color,
      )}
    >
      {initials}
    </span>
  );
}

function StatusChip({ status }: { status: FactStatus }) {
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center gap-1 rounded-full border px-2 text-[11px] font-semibold",
        statusStyles[status],
      )}
    >
      {status === "Active" ? (
        <CheckCircle2 size={12} />
      ) : status === "Expired" ? (
        <AlertCircle size={12} />
      ) : (
        <Clock3 size={12} />
      )}
      {status}
    </span>
  );
}

function Modal({
  children,
  onClose,
  titleId,
}: {
  children: React.ReactNode;
  onClose: () => void;
  titleId: string;
}) {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Close dialog"
        onClick={onClose}
        className="absolute inset-0 bg-slate-950/40"
      />
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative z-10 flex max-h-[92vh] w-full max-w-[790px] flex-col overflow-hidden rounded-xl border border-[#E3E8F2] bg-white shadow-2xl"
      >
        {children}
      </section>
    </div>
  );
}

function Stepper({ step }: { step: 1 | 2 }) {
  const steps = [
    { number: 1, label: "Change the fact" },
    { number: 2, label: "See what will be affected" },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 border-b border-[#E3E8F2] px-5 py-4">
      {steps.map((item) => {
        const active = item.number === step;
        const complete = item.number < step;

        return (
          <div
            key={item.number}
            className={cn(
              "flex items-center gap-2.5 rounded-lg border px-3 py-2.5",
              active
                ? "border-blue-200 bg-blue-50"
                : complete
                  ? "border-emerald-200 bg-emerald-50"
                  : "border-slate-200 bg-white",
            )}
          >
            <span
              className={cn(
                "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                active
                  ? "bg-[#2F5BEA] text-white"
                  : complete
                    ? "bg-emerald-600 text-white"
                    : "bg-slate-100 text-slate-500",
              )}
            >
              {complete ? <Check size={14} /> : item.number}
            </span>
            <span
              className={cn(
                "text-[12px] font-semibold",
                active ? "text-[#14213D]" : "text-slate-500",
              )}
            >
              {item.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function mapRecordToFact(record: FactRecord): Fact {
  const ownerName = record.ownerId
    ? record.ownerId.replace(/^user-/, "").replace(/^\w/, (c) => c.toUpperCase())
    : "Team";
  const initials = ownerName
    .split(/[\s-_]+/)
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() || "TM";
  const avatarColors = [
    "bg-violet-100 text-violet-700",
    "bg-sky-100 text-sky-700",
    "bg-rose-100 text-rose-700",
    "bg-emerald-100 text-emerald-700",
    "bg-amber-100 text-amber-700",
  ];
  const charCode = (record.id.charCodeAt(record.id.length - 1) || 0) % avatarColors.length;

  return {
    id: record.id,
    fact: record.title || record.statement,
    value: record.statement,
    product: record.productId || record.category || "Brand",
    owner: ownerName,
    initials,
    avatarColor: avatarColors[charCode],
    version: record.version || 1,
    expiryDate: record.validUntil || record.validFrom || "2027-12-31",
    status: record.status || getFactStatus(record.validUntil || "2027-12-31"),
    history: [],
  };
}

export default function ProductsFactsPage() {
  const [facts, setFacts] = useState<Fact[]>(initialFacts);
  const [search, setSearch] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("All owners");
  const [statusFilter, setStatusFilter] = useState("All statuses");
  const [expiringOnly, setExpiringOnly] = useState(false);
  const [selectedFact, setSelectedFact] = useState<Fact | null>(null);
  const [editingFact, setEditingFact] = useState<Fact | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [editStep, setEditStep] = useState<1 | 2>(1);
  const [newValue, setNewValue] = useState("");
  const [reason, setReason] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("2026-10-25");
  const [toast, setToast] = useState(false);
  const [showAlerts, setShowAlerts] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newFact, setNewFact] = useState("");
  const [newFactProduct, setNewFactProduct] = useState("");
  const [newFactValue, setNewFactValue] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const loadFacts = async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const records = await listFacts();
      if (Array.isArray(records) && records.length > 0) {
        setFacts(records.map(mapRecordToFact));
      }
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadFacts();
  }, []);

  const openDetail = async (fact: Fact) => {
    setSelectedFact(fact);
    setDetailOpen(true);
    try {
      const historyItems = await getFactHistory(fact.id);
      if (Array.isArray(historyItems) && historyItems.length > 0) {
        const mappedHistory: FactHistory[] = historyItems.map((h) => ({
          version: h.version,
          date: formatDate(h.changedAt || h.validFrom),
          owner: h.owner || h.changedBy || fact.owner,
          note: h.note || `Version ${h.version} update`,
          value: h.statement,
        }));
        setSelectedFact((prev) => (prev && prev.id === fact.id ? { ...prev, history: mappedHistory } : prev));
        setFacts((prev) => prev.map((f) => (f.id === fact.id ? { ...f, history: mappedHistory } : f)));
      }
    } catch {
      // Retain existing history on error
    }
  };

  const summary = useMemo(() => {
    const currentStatuses = facts.map((fact) => ({
      ...fact,
      status: getFactStatus(fact.expiryDate),
    }));

    return {
      total: facts.length,
      expiring: currentStatuses.filter(
        (fact) => fact.status === "Expiring soon",
      ).length,
      expired: currentStatuses.filter((fact) => fact.status === "Expired")
        .length,
    };
  }, [facts]);

  const owners = useMemo(
    () => ["All owners", ...new Set(facts.map((fact) => fact.owner))],
    [facts],
  );

  const filteredFacts = useMemo(() => {
    const term = search.trim().toLowerCase();

    return facts
      .map((fact) => ({
        ...fact,
        status: getFactStatus(fact.expiryDate),
      }))
      .filter((fact) => {
        const matchesSearch =
          !term ||
          [
            fact.id,
            fact.fact,
            fact.value,
            fact.product,
            fact.owner,
          ].some((field) => field.toLowerCase().includes(term));

        const matchesOwner =
          ownerFilter === "All owners" || fact.owner === ownerFilter;

        const matchesStatus =
          statusFilter === "All statuses" || fact.status === statusFilter;

        const matchesExpiring =
          !expiringOnly || fact.status === "Expiring soon";

        return (
          matchesSearch && matchesOwner && matchesStatus && matchesExpiring
        );
      });
  }, [facts, search, ownerFilter, statusFilter, expiringOnly]);

  const openEdit = (fact: Fact) => {
    setEditingFact(fact);
    setNewValue(fact.value);
    setReason("");
    setEffectiveDate("2026-10-25");
    setEditStep(1);
    setDetailOpen(false);
  };

  const confirmChange = async () => {
    if (!editingFact || !newValue.trim() || !reason.trim()) return;

    try {
      await updateFact(editingFact.id, {
        statement: newValue.trim(),
        note: reason.trim(),
      });
    } catch (err) {
      console.warn("Failed to update fact via API, falling back to local state:", err);
    }

    const updatedFact: Fact = {
      ...editingFact,
      value: newValue.trim(),
      fact: editingFact.fact,
      version: editingFact.version + 1,
      expiryDate: editingFact.expiryDate,
      history: [
        {
          version: editingFact.version + 1,
          date: formatDate(effectiveDate),
          owner: editingFact.owner,
          note: reason.trim(),
          value: newValue.trim(),
        },
        ...editingFact.history,
      ],
    };

    setFacts((previous) =>
      previous.map((fact) =>
        fact.id === updatedFact.id ? updatedFact : fact,
      ),
    );

    setSelectedFact(updatedFact);
    setEditingFact(null);
    setToast(true);
    setShowAlerts(false);
  };

  const addFact = async () => {
    if (!newFact.trim() || !newFactProduct.trim() || !newFactValue.trim()) {
      return;
    }

    let createdId = `FACT-${String(40 + facts.length).padStart(3, "0")}`;
    try {
      const res = await createFact({
        title: newFact.trim(),
        statement: newFactValue.trim(),
        factType: "claim",
        category: newFactProduct.trim(),
      });
      if (res?.id) {
        createdId = res.id;
      }
    } catch (err) {
      console.warn("Failed to create fact via API, falling back to local state:", err);
    }

    const fact: Fact = {
      id: createdId,
      fact: newFact.trim(),
      value: newFactValue.trim(),
      product: newFactProduct.trim(),
      owner: "Ananya Sharma",
      initials: "AS",
      avatarColor: "bg-violet-100 text-violet-700",
      version: 1,
      expiryDate: "2027-10-25",
      status: "Active",
      history: [
        {
          version: 1,
          date: "25 Oct 2026",
          owner: "Ananya Sharma",
          note: "New approved fact added.",
          value: newFactValue.trim(),
        },
      ],
    };

    setFacts((previous) => [fact, ...previous]);
    setShowAddDialog(false);
    setNewFact("");
    setNewFactProduct("");
    setNewFactValue("");
    setSelectedFact(fact);
    setDetailOpen(true);
  };

  const runDemoLoading = () => {
    setLoading(true);
    setLoadError(false);
    window.setTimeout(() => setLoading(false), 900);
  };

  return (
    <div className="min-h-full bg-[#F6F8FC] text-[#14213D]">
      <main className="mx-auto w-full max-w-[1600px] space-y-4 p-5">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-[18px] font-semibold leading-6">
              Products and Facts
            </h1>
            <p className="mt-1 text-[12px] text-slate-500">
              The approved facts every piece of content is checked against
            </p>
          </div>

          <button
            type="button"
            onClick={() => setShowAddDialog(true)}
            className="inline-flex min-h-[40px] sm:min-h-[36px] w-full sm:w-auto justify-center items-center gap-2 rounded-lg bg-[#2F5BEA] px-3.5 text-[12px] font-semibold text-white shadow-sm transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2F5BEA] focus-visible:ring-offset-2"
          >
            <Plus size={15} />
            Add fact
          </button>
        </header>

        <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="flex items-center gap-3 rounded-xl border border-[#E3E8F2] bg-white px-4 py-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-[#2F5BEA]">
              <ShieldCheck size={18} />
            </div>
            <div>
              <p className="text-[18px] font-semibold tabular-nums">
                {summary.total === 6 ? 24 : summary.total}
              </p>
              <p className="text-[11px] text-slate-500">Approved facts</p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-xl border border-[#E3E8F2] bg-white px-4 py-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50 text-amber-800">
              <Clock3 size={18} />
            </div>
            <div>
              <p className="text-[18px] font-semibold tabular-nums">
                {summary.expiring === 0 && facts.length === 6
                  ? 3
                  : summary.expiring}
              </p>
              <p className="text-[11px] text-slate-500">Expiring soon</p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-xl border border-[#E3E8F2] bg-white px-4 py-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-red-50 text-red-700">
              <AlertCircle size={18} />
            </div>
            <div>
              <p className="text-[18px] font-semibold tabular-nums">
                {summary.expired === 0 && facts.length === 6
                  ? 1
                  : summary.expired}
              </p>
              <p className="text-[11px] text-slate-500">Expired</p>
            </div>
          </div>
        </section>

        <section className="overflow-hidden rounded-xl border border-[#E3E8F2] bg-white">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E3E8F2] p-3.5">
            <div className="relative min-w-0 w-full sm:w-auto sm:min-w-[220px] flex-1 sm:max-w-[340px]">
              <Search
                size={15}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search facts, products or IDs..."
                aria-label="Search facts"
                className="h-10 sm:h-9 min-h-[40px] sm:min-h-[36px] w-full rounded-lg border border-[#E3E8F2] bg-white pl-9 pr-3 text-[12px] outline-none transition placeholder:text-slate-400 focus:border-[#2F5BEA] focus:ring-2 focus:ring-blue-100"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
              <label className="relative flex-1 sm:flex-none">
                <span className="sr-only">Filter by owner</span>
                <select
                  value={ownerFilter}
                  onChange={(event) => setOwnerFilter(event.target.value)}
                  className="h-10 sm:h-9 min-h-[40px] sm:min-h-[36px] w-full sm:min-w-[130px] appearance-none rounded-lg border border-[#E3E8F2] bg-white pl-3 pr-8 text-[12px] text-slate-700 outline-none focus:border-[#2F5BEA] focus:ring-2 focus:ring-blue-100"
                >
                  {owners.map((owner) => (
                    <option key={owner}>{owner}</option>
                  ))}
                </select>
                <ChevronDown
                  size={13}
                  className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400"
                />
              </label>

              <label className="relative flex-1 sm:flex-none">
                <span className="sr-only">Filter by status</span>
                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                  className="h-10 sm:h-9 min-h-[40px] sm:min-h-[36px] w-full sm:min-w-[130px] appearance-none rounded-lg border border-[#E3E8F2] bg-white pl-3 pr-8 text-[12px] text-slate-700 outline-none focus:border-[#2F5BEA] focus:ring-2 focus:ring-blue-100"
                >
                  {["All statuses", "Active", "Expiring soon", "Expired"].map(
                    (status) => (
                      <option key={status}>{status}</option>
                    ),
                  )}
                </select>
                <ChevronDown
                  size={13}
                  className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400"
                />
              </label>

              <button
                type="button"
                onClick={() => setExpiringOnly((value) => !value)}
                aria-pressed={expiringOnly}
                className={cn(
                  "inline-flex min-h-[40px] sm:min-h-[36px] items-center gap-1.5 rounded-lg border px-3 text-[12px] font-medium transition",
                  expiringOnly
                    ? "border-amber-300 bg-amber-50 text-amber-900"
                    : "border-[#E3E8F2] bg-white text-slate-600 hover:bg-slate-50",
                )}
              >
                <Filter size={13} />
                Expiring soon
              </button>

              <button
                type="button"
                onClick={loadFacts}
                className="hidden min-h-[40px] sm:min-h-[36px] items-center gap-1.5 rounded-lg border border-[#E3E8F2] px-3 text-[12px] text-slate-600 hover:bg-slate-50 sm:inline-flex"
              >
                Refresh
              </button>
            </div>
          </div>

          {loadError ? (
            <ErrorState
              title="Couldn't load facts"
              description="Check your connection and try again. Your work has not been changed."
              onRetry={loadFacts}
              className="m-4"
            />
          ) : loading ? (
            <div className="p-4">
              <LoadingState label="Loading approved facts" rows={5} />
            </div>
          ) : filteredFacts.length === 0 ? (
            <div className="flex flex-col items-center px-5 py-16 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 text-[#2F5BEA]">
                <FileText size={23} />
              </div>
              <h2 className="mt-3 text-[14px] font-semibold">
                {facts.length === 0
                  ? "No facts yet - add your first approved fact"
                  : "No matching facts"}
              </h2>
              <p className="mt-1 max-w-[320px] text-[12px] leading-5 text-slate-500">
                {facts.length === 0
                  ? "Add an approved product fact so content can be checked against it."
                  : "Try changing your search or filters to find the fact you're looking for."}
              </p>
              {facts.length === 0 && (
                <button
                  type="button"
                  onClick={() => setShowAddDialog(true)}
                  className="mt-4 inline-flex h-9 items-center gap-2 rounded-lg bg-[#2F5BEA] px-3 text-[12px] font-semibold text-white"
                >
                  <Plus size={14} />
                  Add your first fact
                </button>
              )}
              {facts.length > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    setSearch("");
                    setOwnerFilter("All owners");
                    setStatusFilter("All statuses");
                    setExpiringOnly(false);
                  }}
                  className="mt-4 text-[12px] font-semibold text-[#2F5BEA] hover:underline"
                >
                  Clear filters
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[950px] border-collapse text-left">
                <thead>
                  <tr className="border-b border-[#E3E8F2] bg-[#FAFBFE]">
                    {[
                      "ID",
                      "Fact",
                      "Product",
                      "Owner",
                      "Version",
                      "Expires",
                      "Used in",
                      "Status",
                      "",
                    ].map((heading) => (
                      <th
                        key={heading}
                        className="whitespace-nowrap px-3 py-3 text-[10px] font-semibold uppercase tracking-wide text-slate-500 first:pl-4"
                      >
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {filteredFacts.map((fact) => (
                    <tr
                      key={fact.id}
                      onClick={() => {
                        void openDetail(fact);
                      }}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          void openDetail(fact);
                        }
                      }}
                      tabIndex={0}
                      className="group cursor-pointer border-b border-slate-100 last:border-0 hover:bg-blue-50/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#2F5BEA]"
                    >
                      <td className="whitespace-nowrap px-3 py-3.5 pl-4">
                        <span className="font-mono text-[11px] font-semibold text-slate-600">
                          {fact.id}
                        </span>
                      </td>

                      <td className="max-w-[240px] px-3 py-3.5">
                        <p className="truncate text-[12px] font-semibold text-slate-800">
                          {fact.fact}
                        </p>
                        <p className="mt-1 truncate text-[11px] text-slate-500">
                          {fact.value}
                        </p>
                      </td>

                      <td className="whitespace-nowrap px-3 py-3.5 text-[12px] text-slate-700">
                        {fact.product}
                      </td>

                      <td className="whitespace-nowrap px-3 py-3.5">
                        <div className="flex items-center gap-2">
                          <Avatar
                            initials={fact.initials}
                            color={fact.avatarColor}
                          />
                          <span className="text-[12px] text-slate-700">
                            {fact.owner}
                          </span>
                        </div>
                      </td>

                      <td className="px-3 py-3.5 text-[12px] text-slate-600">
                        v{fact.version}
                      </td>

                      <td className="whitespace-nowrap px-3 py-3.5 text-[12px] text-slate-600">
                        {formatDate(fact.expiryDate)}
                      </td>

                      <td className="px-3 py-3.5">
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            void openDetail(fact);
                          }}
                          className="text-[12px] font-semibold text-[#2F5BEA] hover:underline"
                        >
                          {fact.id === "FACT-009"
                            ? 4
                            : fact.id === "FACT-014"
                              ? 4
                              : fact.id === "FACT-027"
                                ? 4
                                : 0}
                        </button>
                      </td>

                      <td className="whitespace-nowrap px-3 py-3.5">
                        <StatusChip status={fact.status} />
                      </td>

                      <td className="px-3 py-3.5 text-right">
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            openEdit(fact);
                          }}
                          className="invisible inline-flex h-7 items-center rounded-md border border-[#E3E8F2] bg-white px-2 text-[11px] font-semibold text-slate-700 hover:border-blue-200 hover:text-[#2F5BEA] group-hover:visible group-focus-within:visible"
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!loading && !loadError && filteredFacts.length > 0 && (
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#E3E8F2] px-4 py-3">
              <p className="text-[11px] text-slate-500">
                Showing {filteredFacts.length} of {facts.length} facts
              </p>
              <p className="text-[11px] text-slate-400">
                Demo data · Changes stay in this session
              </p>
            </div>
          )}
        </section>
      </main>

      {detailOpen && selectedFact && (
        <div className="fixed inset-0 z-[80] flex justify-end">
          <button
            type="button"
            aria-label="Close fact details"
            onClick={() => setDetailOpen(false)}
            className="absolute inset-0 bg-slate-950/30"
          />

          <aside
            role="dialog"
            aria-modal="true"
            aria-labelledby="fact-detail-title"
            className="relative flex h-full w-full max-w-[440px] flex-col border-l border-[#E3E8F2] bg-white shadow-2xl"
          >
            <header className="flex items-start justify-between gap-3 border-b border-[#E3E8F2] px-4 py-4">
              <div className="min-w-0">
                <p className="font-mono text-[11px] font-semibold text-slate-500">
                  {selectedFact.id}
                </p>
                <h2
                  id="fact-detail-title"
                  className="mt-1 text-[16px] font-semibold"
                >
                  {selectedFact.fact}
                </h2>
                <div className="mt-2">
                  <StatusChip status={getFactStatus(selectedFact.expiryDate)} />
                </div>
              </div>
              <button
                type="button"
                aria-label="Close detail panel"
                onClick={() => setDetailOpen(false)}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100"
              >
                <X size={17} />
              </button>
            </header>

            <div className="flex-1 space-y-5 overflow-y-auto px-4 py-4">
              <section>
                <h3 className="text-[12px] font-semibold text-slate-600">
                  Approved value
                </h3>
                <div className="mt-2 rounded-lg border border-blue-100 bg-blue-50 p-3">
                  <p className="text-[13px] leading-5 text-slate-800">
                    {selectedFact.value}
                  </p>
                </div>
              </section>

              <section className="grid grid-cols-2 gap-2">
                <div className="rounded-lg border border-[#E3E8F2] p-3">
                  <p className="text-[11px] text-slate-500">Product</p>
                  <p className="mt-1.5 text-[12px] font-semibold">
                    {selectedFact.product}
                  </p>
                </div>
                <div className="rounded-lg border border-[#E3E8F2] p-3">
                  <p className="text-[11px] text-slate-500">Version</p>
                  <p className="mt-1.5 text-[12px] font-semibold">
                    v{selectedFact.version}
                  </p>
                </div>
                <div className="rounded-lg border border-[#E3E8F2] p-3">
                  <p className="text-[11px] text-slate-500">Owner</p>
                  <div className="mt-1.5 flex items-center gap-2">
                    <Avatar
                      initials={selectedFact.initials}
                      color={selectedFact.avatarColor}
                    />
                    <span className="text-[12px] font-medium">
                      {selectedFact.owner}
                    </span>
                  </div>
                </div>
                <div className="rounded-lg border border-[#E3E8F2] p-3">
                  <p className="text-[11px] text-slate-500">Expires</p>
                  <p className="mt-1.5 flex items-center gap-1.5 text-[12px] font-semibold">
                    <CalendarDays size={13} className="text-slate-400" />
                    {formatDate(selectedFact.expiryDate)}
                  </p>
                </div>
              </section>

              <section>
                <div className="mb-2 flex items-center gap-2">
                  <History size={15} className="text-slate-500" />
                  <h3 className="text-[13px] font-semibold">Version history</h3>
                </div>

                <div className="space-y-3">
                  {selectedFact.history.map((entry, index) => (
                    <div key={`${entry.version}-${entry.date}`} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <span
                          className={cn(
                            "flex h-6 w-6 items-center justify-center rounded-full border text-[10px] font-semibold",
                            index === 0
                              ? "border-blue-200 bg-blue-50 text-[#2F5BEA]"
                              : "border-slate-200 bg-white text-slate-500",
                          )}
                        >
                          {index === 0 ? <Check size={12} /> : `v${entry.version}`}
                        </span>
                        {index < selectedFact.history.length - 1 && (
                          <span className="mt-1 w-px flex-1 bg-slate-200" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1 rounded-lg border border-slate-100 p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="text-[12px] font-semibold">
                            Version {entry.version}
                            {index === 0 ? " · Current" : ""}
                          </p>
                          <span className="text-[10px] text-slate-500">
                            {entry.date}
                          </span>
                        </div>
                        <p className="mt-1 text-[12px] leading-5 text-slate-600">
                          {entry.note}
                        </p>
                        <p className="mt-2 rounded-md bg-slate-50 p-2 text-[11px] leading-4 text-slate-700">
                          {entry.value}
                        </p>
                        <p className="mt-2 text-[10px] text-slate-500">
                          Changed by {entry.owner}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <section>
                <h3 className="text-[13px] font-semibold">Linked content</h3>
                <p className="mt-1 text-[11px] text-slate-500">
                  Content that references this fact may need a review when the
                  approved value changes.
                </p>
                <div className="mt-2 space-y-2">
                  {initialImpactItems
                    .slice(
                      0,
                      selectedFact.id === "FACT-009" ? 3 : 2,
                    )
                    .map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center gap-2.5 rounded-lg border border-[#E3E8F2] p-2.5"
                      >
                        <FileText size={15} className="text-slate-400" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-[12px] font-medium">
                            {item.title}
                          </p>
                          <p className="mt-0.5 text-[10px] text-slate-500">
                            {item.id} · {item.channel}
                          </p>
                        </div>
                        <ChevronRight size={14} className="text-slate-400" />
                      </div>
                    ))}
                </div>
              </section>
            </div>

            <footer className="flex gap-2 border-t border-[#E3E8F2] px-4 py-3">
              <button
                type="button"
                onClick={() => setDetailOpen(false)}
                className="h-10 sm:h-9 min-h-[40px] sm:min-h-[36px] flex-1 rounded-lg border border-[#E3E8F2] text-[12px] font-semibold text-slate-700 hover:bg-slate-50"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => openEdit(selectedFact)}
                className="inline-flex h-10 sm:h-9 min-h-[40px] sm:min-h-[36px] flex-1 items-center justify-center gap-2 rounded-lg bg-[#2F5BEA] text-[12px] font-semibold text-white hover:bg-blue-700"
              >
                Edit fact
                <ArrowRight size={14} />
              </button>
            </footer>
          </aside>
        </div>
      )}

      {editingFact && (
        <Modal
          titleId="edit-fact-title"
          onClose={() => setEditingFact(null)}
        >
          <header className="flex items-start justify-between gap-3 px-5 pb-4 pt-5">
            <div>
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-[#2F5BEA]">
                  <ShieldCheck size={17} />
                </div>
                <h2 id="edit-fact-title" className="text-[16px] font-semibold">
                  Edit fact
                </h2>
              </div>
              <p className="mt-2 text-[12px] text-slate-500">
                {editingFact.id} · {editingFact.product}
              </p>
            </div>
            <button
              type="button"
              aria-label="Close edit dialog"
              onClick={() => setEditingFact(null)}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100"
            >
              <X size={17} />
            </button>
          </header>

          <Stepper step={editStep} />

          <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
            {editStep === 1 ? (
              <>
                <div>
                  <label className="text-[12px] font-semibold text-slate-700">
                    Current approved value
                  </label>
                  <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-[12px] leading-5 text-slate-500 line-through decoration-slate-400">
                    {editingFact.value}
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="new-fact-value"
                    className="text-[12px] font-semibold text-slate-700"
                  >
                    New value <span className="text-red-600">*</span>
                  </label>
                  <textarea
                    id="new-fact-value"
                    rows={3}
                    value={newValue}
                    onChange={(event) => setNewValue(event.target.value)}
                    placeholder="Enter the updated approved value..."
                    className="mt-2 w-full resize-y rounded-lg border border-[#E3E8F2] px-3 py-2.5 text-[13px] leading-5 outline-none focus:border-[#2F5BEA] focus:ring-2 focus:ring-blue-100"
                  />
                  <p className="mt-1 text-[11px] text-slate-500">
                    This wording will become the new approved source of truth.
                  </p>
                </div>

                <div>
                  <label
                    htmlFor="fact-change-reason"
                    className="text-[12px] font-semibold text-slate-700"
                  >
                    Reason for change <span className="text-red-600">*</span>
                  </label>
                  <textarea
                    id="fact-change-reason"
                    rows={2}
                    value={reason}
                    onChange={(event) => setReason(event.target.value)}
                    placeholder="Explain why this fact needs to change..."
                    className="mt-2 w-full resize-y rounded-lg border border-[#E3E8F2] px-3 py-2.5 text-[13px] leading-5 outline-none focus:border-[#2F5BEA] focus:ring-2 focus:ring-blue-100"
                  />
                </div>

                <div>
                  <label
                    htmlFor="effective-date"
                    className="text-[12px] font-semibold text-slate-700"
                  >
                    Effective date
                  </label>
                  <div className="relative mt-2">
                    <CalendarDays
                      size={15}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    />
                    <input
                      id="effective-date"
                      type="date"
                      value={effectiveDate}
                      onChange={(event) => setEffectiveDate(event.target.value)}
                      className="h-10 w-full rounded-lg border border-[#E3E8F2] bg-white pl-9 pr-3 text-[12px] outline-none focus:border-[#2F5BEA] focus:ring-2 focus:ring-blue-100"
                    />
                  </div>
                </div>

                <div className="flex items-start gap-2 rounded-lg border border-blue-100 bg-blue-50 p-3">
                  <Info size={15} className="mt-0.5 shrink-0 text-blue-700" />
                  <p className="text-[11px] leading-5 text-slate-700">
                    BrandGuard will preview the published content linked to this
                    fact before you confirm the change.
                  </p>
                </div>
              </>
            ) : (
              <>
                <div className="flex items-start gap-2.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3">
                  <CheckCircle2
                    size={17}
                    className="mt-0.5 shrink-0 text-emerald-700"
                  />
                  <div>
                    <p className="text-[12px] font-semibold text-emerald-900">
                      This change affects 3 published items owned by 2 people
                    </p>
                    <p className="mt-1 text-[11px] leading-4 text-emerald-800">
                      Only linked content is included in this impact preview.
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  {initialImpactItems.map((item) => (
                    <article
                      key={item.id}
                      className="overflow-hidden rounded-lg border border-[#E3E8F2]"
                    >
                      <div className="flex items-center gap-2.5 border-b border-slate-100 px-3 py-2.5">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-slate-100 text-slate-500">
                          <FileText size={16} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-[12px] font-semibold text-slate-800">
                            {item.title}
                          </p>
                          <p className="mt-0.5 text-[10px] text-slate-500">
                            {item.id} · {item.channel}
                          </p>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Avatar
                            initials={item.initials}
                            color={item.avatarColor}
                          />
                          <span className="hidden text-[11px] text-slate-600 sm:inline">
                            {item.owner}
                          </span>
                        </div>
                      </div>

                      <div className="grid gap-3 p-3 sm:grid-cols-2">
                        <div>
                          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                            Current text
                          </p>
                          <p className="rounded-md bg-slate-50 p-2.5 text-[11px] leading-5 text-slate-600">
                            {item.currentText}
                          </p>
                        </div>
                        <div>
                          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-800">
                            Suggested correction
                          </p>
                          <p className="rounded-md border border-emerald-100 bg-emerald-50/60 p-2.5 text-[11px] leading-5 text-slate-700">
                            {item.suggestedText
                              .split(/(helps remove excess oil|Help remove excess oil)/gi)
                              .map((part, index) =>
                                /helps remove excess oil|Help remove excess oil/i.test(
                                  part,
                                ) ? (
                                  <mark
                                    key={index}
                                    className="rounded bg-emerald-200 px-0.5 font-semibold text-emerald-950"
                                  >
                                    {part}
                                  </mark>
                                ) : (
                                  <span key={index}>{part}</span>
                                ),
                              )}
                          </p>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>

                <p className="flex items-start gap-2 text-[11px] leading-5 text-slate-600">
                  <ShieldCheck
                    size={14}
                    className="mt-0.5 shrink-0 text-emerald-700"
                  />
                  Only these owners will be notified. Nobody else is alerted.
                </p>
              </>
            )}
          </div>

          <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-[#E3E8F2] bg-white px-5 py-3.5">
            <button
              type="button"
              onClick={() => {
                if (editStep === 2) {
                  setEditStep(1);
                } else {
                  setEditingFact(null);
                }
              }}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-[#E3E8F2] px-3 text-[12px] font-semibold text-slate-700 hover:bg-slate-50"
            >
              {editStep === 1 ? (
                <>
                  <X size={14} />
                  Cancel
                </>
              ) : (
                <>
                  <ArrowLeft size={14} />
                  Back
                </>
              )}
            </button>

            {editStep === 1 ? (
              <button
                type="button"
                disabled={!newValue.trim() || !reason.trim() || !effectiveDate}
                onClick={() => setEditStep(2)}
                className="inline-flex h-9 items-center gap-2 rounded-lg bg-[#2F5BEA] px-4 text-[12px] font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
              >
                See what will be affected
                <ArrowRight size={14} />
              </button>
            ) : (
              <button
                type="button"
                onClick={confirmChange}
                className="inline-flex h-9 items-center gap-2 rounded-lg bg-[#2F5BEA] px-4 text-[12px] font-semibold text-white hover:bg-blue-700"
              >
                <Bell size={14} />
                Confirm and notify owners
              </button>
            )}
          </footer>
        </Modal>
      )}

      {showAddDialog && (
        <Modal
          titleId="add-fact-title"
          onClose={() => setShowAddDialog(false)}
        >
          <header className="flex items-center justify-between border-b border-[#E3E8F2] px-5 py-4">
            <div>
              <h2 id="add-fact-title" className="text-[16px] font-semibold">
                Add approved fact
              </h2>
              <p className="mt-1 text-[12px] text-slate-500">
                Add a fact for BrandGuard to check against.
              </p>
            </div>
            <button
              type="button"
              aria-label="Close add fact dialog"
              onClick={() => setShowAddDialog(false)}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100"
            >
              <X size={17} />
            </button>
          </header>

          <div className="space-y-4 px-5 py-5">
            <div>
              <label
                htmlFor="fact-title"
                className="text-[12px] font-semibold text-slate-700"
              >
                Fact title
              </label>
              <input
                id="fact-title"
                value={newFact}
                onChange={(event) => setNewFact(event.target.value)}
                placeholder="e.g. Daily sunscreen protection"
                className="mt-2 h-10 w-full rounded-lg border border-[#E3E8F2] px-3 text-[12px] outline-none focus:border-[#2F5BEA] focus:ring-2 focus:ring-blue-100"
              />
            </div>

            <div>
              <label
                htmlFor="fact-product"
                className="text-[12px] font-semibold text-slate-700"
              >
                Product
              </label>
              <input
                id="fact-product"
                value={newFactProduct}
                onChange={(event) => setNewFactProduct(event.target.value)}
                placeholder="Product or product line"
                className="mt-2 h-10 w-full rounded-lg border border-[#E3E8F2] px-3 text-[12px] outline-none focus:border-[#2F5BEA] focus:ring-2 focus:ring-blue-100"
              />
            </div>

            <div>
              <label
                htmlFor="fact-value"
                className="text-[12px] font-semibold text-slate-700"
              >
                Approved value
              </label>
              <textarea
                id="fact-value"
                rows={3}
                value={newFactValue}
                onChange={(event) => setNewFactValue(event.target.value)}
                placeholder="Enter the exact approved wording..."
                className="mt-2 w-full rounded-lg border border-[#E3E8F2] px-3 py-2.5 text-[12px] leading-5 outline-none focus:border-[#2F5BEA] focus:ring-2 focus:ring-blue-100"
              />
            </div>
          </div>

          <footer className="flex justify-end gap-2 border-t border-[#E3E8F2] px-5 py-3.5">
            <button
              type="button"
              onClick={() => setShowAddDialog(false)}
              className="h-9 rounded-lg border border-[#E3E8F2] px-3 text-[12px] font-semibold text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={
                !newFact.trim() ||
                !newFactProduct.trim() ||
                !newFactValue.trim()
              }
              onClick={addFact}
              className="inline-flex h-9 items-center gap-2 rounded-lg bg-[#2F5BEA] px-3 text-[12px] font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Plus size={14} />
              Add fact
            </button>
          </footer>
        </Modal>
      )}

      {toast && (
        <div
          role="status"
          className="fixed bottom-5 right-5 z-[120] flex w-[min(420px,calc(100vw-40px))] items-start gap-3 rounded-xl border border-emerald-200 bg-white p-4 shadow-xl"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-800">
            <CheckCircle2 size={17} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-semibold text-slate-900">
              Fact updated successfully
            </p>
            <p className="mt-1 text-[11px] leading-4 text-slate-500">
              The approved value has been updated. Impacted owners can be
              notified through the alerts workflow.
            </p>
            <button
              type="button"
              onClick={() => {
                setToast(false);
                setShowAlerts(true);
              }}
              className="mt-2 text-[12px] font-semibold text-[#2F5BEA] hover:underline"
            >
              View alerts
            </button>
          </div>
          <button
            type="button"
            aria-label="Dismiss notification"
            onClick={() => setToast(false)}
            className="text-slate-400 hover:text-slate-700"
          >
            <X size={15} />
          </button>
        </div>
      )}

      {showAlerts && (
        <div className="fixed inset-0 z-[100] flex justify-end">
          <button
            type="button"
            aria-label="Close alerts"
            onClick={() => setShowAlerts(false)}
            className="absolute inset-0 bg-slate-950/30"
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-labelledby="alerts-title"
            className="relative flex h-full w-full max-w-[400px] flex-col border-l border-[#E3E8F2] bg-white shadow-2xl"
          >
            <header className="flex items-center justify-between border-b border-[#E3E8F2] px-4 py-4">
              <div>
                <h2 id="alerts-title" className="text-[16px] font-semibold">
                  Owner alerts
                </h2>
                <p className="mt-1 text-[11px] text-slate-500">
                  Impacted content owners for the fact change
                </p>
              </div>
              <button
                type="button"
                aria-label="Close alerts panel"
                onClick={() => setShowAlerts(false)}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100"
              >
                <X size={17} />
              </button>
            </header>

            <div className="flex-1 space-y-3 overflow-y-auto p-4">
              {[...new Map(initialImpactItems.map((item) => [item.owner, item])).values()].map(
                (item) => (
                  <div
                    key={item.owner}
                    className="flex items-start gap-3 rounded-lg border border-[#E3E8F2] p-3"
                  >
                    <Avatar
                      initials={item.initials}
                      color={item.avatarColor}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-[12px] font-semibold">{item.owner}</p>
                      <p className="mt-1 text-[11px] leading-4 text-slate-500">
                        Review updated approved wording in {item.title}.
                      </p>
                      <span className="mt-2 inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 text-[10px] font-semibold text-amber-900">
                        <Clock3 size={11} />
                        Pending review
                      </span>
                    </div>
                  </div>
                ),
              )}
              <p className="rounded-lg bg-slate-50 p-3 text-[11px] leading-5 text-slate-600">
                Demo behavior: these alerts are displayed locally. Connect the
                alerts API to deliver and track real notifications.
              </p>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
