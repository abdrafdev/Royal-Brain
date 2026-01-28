import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import Alert from "@/components/ui/Alert";
import Card from "@/components/ui/Card";
import PageShell from "@/components/ui/PageShell";
import { AUTH_COOKIE } from "@/lib/constants";
import { getBackendUrl } from "@/lib/server-env";
import UserTable from "./UserTable";

type User = {
  id: number;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

export default async function AdminUsersPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value;

  if (!token) redirect("/login");

  const backendUrl = getBackendUrl();

  // Check if current user is admin
  const meResp = await fetch(`${backendUrl}/users/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (meResp.status === 401 || meResp.status === 403) redirect("/logout");

  if (!meResp.ok) {
    return (
      <PageShell title="User Management" description="Admin panel">
        <Alert tone="error" title={`Backend error ${meResp.status}`}>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>
            {await meResp.text()}
          </pre>
        </Alert>
      </PageShell>
    );
  }

  const me = (await meResp.json()) as { role?: string };

  if (me.role !== "ADMIN") {
    return (
      <PageShell title="User Management" description="Admin panel">
        <Alert tone="error" title="Access Denied">
          Only administrators can access this page.
        </Alert>
      </PageShell>
    );
  }

  // Fetch users
  const usersResp = await fetch(`${backendUrl}/users`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!usersResp.ok) {
    return (
      <PageShell title="User Management" description="Admin panel">
        <Alert tone="error" title={`Failed to load users (${usersResp.status})`}>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>
            {await usersResp.text()}
          </pre>
        </Alert>
      </PageShell>
    );
  }

  const users = (await usersResp.json()) as User[];

  return (
    <PageShell title="User Management" description="Admin panel">
      <Card
        title="Users"
        description={`${users.length} total users`}
      >
        <UserTable users={users} />
      </Card>
    </PageShell>
  );
}
