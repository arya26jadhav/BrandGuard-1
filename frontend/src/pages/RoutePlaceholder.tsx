import { useLocation } from "react-router-dom";
import { Construction } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";

const routeDetails: Record<string, { title: string; description: string }> = {
  "/review-queue": {
    title: "Review Queue",
    description: "Review submitted content, leave feedback, and approve only when it meets the brand standard.",
  },
  "/content": {
    title: "Content",
    description: "Check drafts against GreenGlow's approved facts, guidelines, and brand assets before publication.",
  },
  "/guidelines": {
    title: "Brand Guidelines",
    description: "One trusted place for the rules, approved language, disclaimers, and assets your team uses.",
  },
  "/facts": {
    title: "Products and Facts",
    description: "Keep product details current and trace each approved fact to the content that uses it.",
  },
  "/alerts": {
    title: "Fact Change Alerts",
    description: "See which published or in-progress content may be affected when an approved fact changes.",
  },
  "/analytics": {
    title: "Analytics",
    description: "Understand review trends, recurring issues, and where content needs attention.",
  },
  "/settings": {
    title: "Settings",
    description: "Workspace and team settings.",
  },
};

export default function RoutePlaceholder() {
  const location = useLocation();
  const details = routeDetails[location.pathname] ?? {
    title: "Page not found",
    description: "The page you're looking for isn't available in this demo.",
  };

  return (
    <>
      <PageHeader
        eyebrow="GreenGlow workspace"
        title={details.title}
        description={details.description}
      />
      <div className="surface-card p-5 sm:p-6">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-brand">
            <Construction size={19} />
          </div>
          <div>
            <h2 className="font-semibold text-navy">Settings & Tools</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              This route is connected.
            </p>
          </div>
        </div>
        <EmptyState
          title="Section under development"
          description="Additional management settings and integrations will be available here."
          icon={<Construction size={22} />}
          actionLabel="Open content"
          onAction={() => {
            window.location.href = "/content";
          }}
        />
      </div>
    </>
  );
}
