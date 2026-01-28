import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import Alert from "@/components/ui/Alert";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import PageShell from "@/components/ui/PageShell";
import Select from "@/components/ui/Select";
import { AUTH_COOKIE } from "@/lib/constants";
import { getBackendUrl } from "@/lib/server-env";

type PageProps = {
  params: Promise<{ personId: string }>;
  searchParams: Promise<{
    direction?: string;
    depth?: string;
  }>;
};

type Direction = "ancestors" | "descendants" | "both";

type TreeLevel = {
  level: number;
  person_ids: number[];
};

type PersonNode = {
  id: number;
  primary_name: string;
  birth_date: string | null;
  death_date: string | null;
};

type GenealogyTree = {
  root_person_id: number;
  direction: Direction;
  depth: number;
  nodes: PersonNode[];
  edges: unknown[];
  levels_ancestors: TreeLevel[] | null;
  levels_descendants: TreeLevel[] | null;
};

type Issue = {
  severity: "error" | "warning";
  code: string;
  message: string;
  person_id: number | null;
  relationship_id: number | null;
};

type CheckResponse = {
  root_person_id: number;
  depth: number;
  issues: Issue[];
};

function parseDirection(v: string | undefined): Direction {
  if (v === "ancestors" || v === "descendants" || v === "both") return v;
  return "ancestors";
}

function parseDepth(v: string | undefined): number {
  const n = Number.parseInt(v ?? "4", 10);
  if (!Number.isFinite(n)) return 4;
  return Math.max(1, Math.min(n, 10));
}

function fmtLife(p: PersonNode | undefined): string {
  if (!p) return "";
  const b = p.birth_date ?? "?";
  const d = p.death_date ?? "?";
  if (p.birth_date || p.death_date) return `${b} – ${d}`;
  return "";
}

function LevelColumn({
  title,
  levels,
  nodesById,
}: {
  title: string;
  levels: TreeLevel[] | null;
  nodesById: Map<number, PersonNode>;
}) {
  if (!levels || levels.length === 0) return null;

  return (
    <Card title={title} padded={false}>
      <div
        style={{
          display: "flex",
          gap: 12,
          overflowX: "auto",
          padding: "14px 16px 12px",
        }}
      >
        {levels.map((lvl) => (
          <div
            key={lvl.level}
            className="card"
            style={{ minWidth: 220, boxShadow: "none", padding: 12, borderRadius: 10 }}
          >
            <div className="subtle" style={{ fontSize: 12 }}>
              Generation {lvl.level}
            </div>
            <ul style={{ marginTop: 8, paddingLeft: 14 }}>
              {lvl.person_ids.map((id) => {
                const p = nodesById.get(id);
                return (
                  <li key={id} style={{ marginBottom: 8 }}>
                    <div style={{ fontWeight: 700 }}>{p?.primary_name ?? `(Person ${id})`}</div>
                    {p ? (
                      <div className="subtle" style={{ fontSize: 12 }}>
                        {fmtLife(p)}
                      </div>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default async function PersonGenealogyPage({ params, searchParams }: PageProps) {
  const { personId } = await params;
  const sp = await searchParams;

  const direction = parseDirection(sp.direction);
  const depth = parseDepth(sp.depth);

  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value;
  if (!token) redirect("/login");

  const backendUrl = getBackendUrl();

  const [treeResp, checkResp] = await Promise.all([
    fetch(
      `${backendUrl}/genealogy/persons/${personId}/tree?direction=${direction}&depth=${depth}&include_marriages=true`,
      {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      },
    ),
    fetch(`${backendUrl}/genealogy/persons/${personId}/checks?depth=${depth}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    }),
  ]);

  if (treeResp.status === 401 || treeResp.status === 403) redirect("/logout");

  if (!treeResp.ok) {
    const body = await treeResp.text();
    return (
      <PageShell title="Genealogy" description="Tree view">
        <Alert tone="error" title={`Backend error ${treeResp.status}`}>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>{body}</pre>
        </Alert>
      </PageShell>
    );
  }

  const tree = (await treeResp.json()) as GenealogyTree;
  const checks = checkResp.ok
    ? ((await checkResp.json()) as CheckResponse)
    : ({ root_person_id: tree.root_person_id, depth, issues: [] } satisfies CheckResponse);

  const nodesById = new Map(tree.nodes.map((n) => [n.id, n]));
  const root = nodesById.get(tree.root_person_id);

  const errors = checks.issues.filter((i) => i.severity === "error");
  const warnings = checks.issues.filter((i) => i.severity === "warning");

  return (
    <PageShell title="Genealogy Tree" description="Multi-generation view">
      <Card
        title={root?.primary_name ?? `(Person ${personId})`}
        description={fmtLife(root)}
        actions={
          <form method="get" className="row" style={{ gap: 8 }}>
            <Select name="direction" defaultValue={direction}>
              <option value="ancestors">Ancestors</option>
              <option value="descendants">Descendants</option>
              <option value="both">Both</option>
            </Select>
            <Select name="depth" defaultValue={depth.toString()}>
              {[2, 3, 4, 5, 6, 7, 8].map((d) => (
                <option key={d} value={d}>
                  Depth {d}
                </option>
              ))}
            </Select>
            <button type="submit" style={{ display: "none" }}>
              Apply
            </button>
          </form>
        }
      >
        <div className="row" style={{ gap: 10, marginBottom: 12 }}>
          <Badge tone="info">{direction}</Badge>
          <Badge tone="success">Depth {depth}</Badge>
          <Badge tone="neutral">Nodes {tree.nodes.length}</Badge>
        </div>
        <div className="subtle" style={{ fontSize: 13 }}>
          Select a direction and depth to regenerate the tree. Marriages are included for context.
        </div>
      </Card>

      <LevelColumn title="Ancestors" levels={tree.levels_ancestors} nodesById={nodesById} />
      <LevelColumn title="Descendants" levels={tree.levels_descendants} nodesById={nodesById} />

      <Card title="Timeline consistency" description="Automatic checks on the visible subgraph">
        <div className="row" style={{ gap: 10, marginBottom: 10 }}>
          <Badge tone={errors.length ? "error" : "success"}>
            {errors.length ? `${errors.length} error(s)` : "No errors"}
          </Badge>
          <Badge tone={warnings.length ? "warning" : "neutral"}>
            {warnings.length ? `${warnings.length} warning(s)` : "No warnings"}
          </Badge>
        </div>

        {checks.issues.length ? (
          <div className="grid" style={{ gap: 10 }}>
            {checks.issues.map((i, idx) => (
              <Alert
                key={idx}
                tone={i.severity === "error" ? "error" : "warning"}
                dense
                title={`${i.code}`}
              >
                <div>{i.message}</div>
                <div className="subtle" style={{ fontSize: 12, marginTop: 4 }}>
                  {i.person_id ? `person:${i.person_id} ` : ""}
                  {i.relationship_id ? `rel:${i.relationship_id}` : ""}
                </div>
              </Alert>
            ))}
          </div>
        ) : (
          <Alert tone="success">No issues detected in this subgraph.</Alert>
        )}
      </Card>

      <Card title="Navigation" padded={false}>
        <div className="row-between" style={{ padding: "14px 16px" }}>
          <Link href="/dashboard/genealogy" className="subtle">
            ← Back to list
          </Link>
          <Link href="/dashboard" className="subtle">
            Dashboard
          </Link>
        </div>
      </Card>
    </PageShell>
  );
}
