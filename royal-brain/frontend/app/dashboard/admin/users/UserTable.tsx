"use client";

import { useState } from "react";
import Badge from "@/components/ui/Badge";
import Alert from "@/components/ui/Alert";

type User = {
  id: number;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

type Props = {
  users: User[];
};

export default function UserTable({ users: initialUsers }: Props) {
  const [users, setUsers] = useState<User[]>(initialUsers);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserPassword, setNewUserPassword] = useState("");
  const [newUserRole, setNewUserRole] = useState("VIEWER");

  const [editUserRole, setEditUserRole] = useState("VIEWER");
  const [editUserActive, setEditUserActive] = useState(true);


  const handleAddUser = async () => {
    if (!newUserEmail || !newUserPassword) {
      setError("Email and password are required");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const resp = await fetch(`/api/backend/users`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: newUserEmail,
          password: newUserPassword,
          role: newUserRole,
        }),
      });

      if (!resp.ok) {
        const errorText = await resp.text();
        throw new Error(errorText || `Failed to create user (${resp.status})`);
      }

      const newUser = await resp.json();
      setUsers([...users, newUser]);
      setSuccess(`User ${newUser.email} created successfully`);
      setShowAddModal(false);
      setNewUserEmail("");
      setNewUserPassword("");
      setNewUserRole("VIEWER");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleEditUser = async () => {
    if (!selectedUser) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const resp = await fetch(`/api/backend/users/${selectedUser.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          role: editUserRole,
          is_active: editUserActive,
        }),
      });

      if (!resp.ok) {
        const errorText = await resp.text();
        throw new Error(errorText || `Failed to update user (${resp.status})`);
      }

      const updatedUser = await resp.json();
      setUsers(users.map((u) => (u.id === updatedUser.id ? updatedUser : u)));
      setSuccess(`User ${updatedUser.email} updated successfully`);
      setShowEditModal(false);
      setSelectedUser(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUser) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const resp = await fetch(`/api/backend/users/${selectedUser.id}`, {
        method: "DELETE",
      });

      if (!resp.ok) {
        const errorText = await resp.text();
        throw new Error(errorText || `Failed to delete user (${resp.status})`);
      }

      setUsers(users.filter((u) => u.id !== selectedUser.id));
      setSuccess(`User ${selectedUser.email} deleted successfully`);
      setShowDeleteModal(false);
      setSelectedUser(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {error && (
        <Alert tone="error" title="Error" dense>
          {error}
        </Alert>
      )}
      {success && (
        <Alert tone="success" title="Success" dense>
          {success}
        </Alert>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <button
          onClick={() => setShowAddModal(true)}
          style={{
            padding: "8px 14px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: "var(--panel-soft)",
            color: "var(--text)",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          + Add User
        </button>
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              ID
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Email
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Role
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Status
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Created
            </th>
            <th style={{ textAlign: "right", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id} style={{ borderBottom: "1px solid var(--border)" }}>
              <td style={{ padding: "10px 4px", fontSize: 13 }}>#{user.id}</td>
              <td style={{ padding: "10px 4px", fontSize: 13 }}>{user.email}</td>
              <td style={{ padding: "10px 4px", fontSize: 13 }}>
                <Badge
                  tone={
                    user.role === "ADMIN" ? "error" : user.role === "RESEARCHER" ? "info" : "neutral"
                  }
                >
                  {user.role}
                </Badge>
              </td>
              <td style={{ padding: "10px 4px", fontSize: 13 }}>
                <Badge tone={user.is_active ? "success" : "neutral"}>
                  {user.is_active ? "Active" : "Inactive"}
                </Badge>
              </td>
              <td style={{ padding: "10px 4px", fontSize: 13, color: "var(--muted)" }}>
                {new Date(user.created_at).toLocaleDateString()}
              </td>
              <td style={{ padding: "10px 4px", fontSize: 13, textAlign: "right" }}>
                <button
                  onClick={() => {
                    setSelectedUser(user);
                    setEditUserRole(user.role);
                    setEditUserActive(user.is_active);
                    setShowEditModal(true);
                  }}
                  style={{
                    padding: "4px 10px",
                    marginRight: 6,
                    borderRadius: 6,
                    border: "1px solid var(--border)",
                    background: "transparent",
                    color: "var(--text)",
                    cursor: "pointer",
                    fontSize: 12,
                  }}
                >
                  Edit
                </button>
                <button
                  onClick={() => {
                    setSelectedUser(user);
                    setShowDeleteModal(true);
                  }}
                  style={{
                    padding: "4px 10px",
                    borderRadius: 6,
                    border: "1px solid var(--border)",
                    background: "transparent",
                    color: "var(--error)",
                    cursor: "pointer",
                    fontSize: 12,
                  }}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Add User Modal */}
      {showAddModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setShowAddModal(false)}
        >
          <div
            style={{
              background: "var(--panel)",
              borderRadius: 12,
              padding: 24,
              minWidth: 400,
              border: "1px solid var(--border)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 16, fontWeight: 700 }}>Add New User</h3>
            <div style={{ display: "grid", gap: 12, marginBottom: 16 }}>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  Email
                </label>
                <input
                  type="email"
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  placeholder="user@example.com"
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "var(--panel-soft)",
                    color: "var(--text)",
                  }}
                />
              </div>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  Password
                </label>
                <input
                  type="password"
                  value={newUserPassword}
                  onChange={(e) => setNewUserPassword(e.target.value)}
                  placeholder="••••••••"
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "var(--panel-soft)",
                    color: "var(--text)",
                  }}
                />
              </div>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  Role
                </label>
                <select
                  value={newUserRole}
                  onChange={(e) => setNewUserRole(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "var(--panel-soft)",
                    color: "var(--text)",
                  }}
                >
                  <option value="VIEWER">Viewer</option>
                  <option value="RESEARCHER">Researcher</option>
                  <option value="ADMIN">Admin</option>
                </select>
              </div>
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowAddModal(false)}
                disabled={loading}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "transparent",
                  color: "var(--text)",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleAddUser}
                disabled={loading}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "var(--panel-soft)",
                  color: "var(--text)",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                {loading ? "Creating..." : "Create User"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {showEditModal && selectedUser && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setShowEditModal(false)}
        >
          <div
            style={{
              background: "var(--panel)",
              borderRadius: 12,
              padding: 24,
              minWidth: 400,
              border: "1px solid var(--border)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 16, fontWeight: 700 }}>Edit User</h3>
            <p style={{ marginBottom: 16, fontSize: 13, color: "var(--muted)" }}>
              {selectedUser.email}
            </p>
            <div style={{ display: "grid", gap: 12, marginBottom: 16 }}>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  Role
                </label>
                <select
                  value={editUserRole}
                  onChange={(e) => setEditUserRole(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "var(--panel-soft)",
                    color: "var(--text)",
                  }}
                >
                  <option value="VIEWER">Viewer</option>
                  <option value="RESEARCHER">Researcher</option>
                  <option value="ADMIN">Admin</option>
                </select>
              </div>
              <div>
                <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={editUserActive}
                    onChange={(e) => setEditUserActive(e.target.checked)}
                  />
                  <span style={{ fontSize: 13, fontWeight: 600 }}>Active</span>
                </label>
              </div>
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowEditModal(false)}
                disabled={loading}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "transparent",
                  color: "var(--text)",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleEditUser}
                disabled={loading}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "var(--panel-soft)",
                  color: "var(--text)",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                {loading ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete User Modal */}
      {showDeleteModal && selectedUser && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setShowDeleteModal(false)}
        >
          <div
            style={{
              background: "var(--panel)",
              borderRadius: 12,
              padding: 24,
              minWidth: 400,
              border: "1px solid var(--border)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 16, fontWeight: 700, color: "var(--error)" }}>
              Delete User
            </h3>
            <p style={{ marginBottom: 16, fontSize: 14 }}>
              Are you sure you want to delete <strong>{selectedUser.email}</strong>? This action
              cannot be undone.
            </p>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowDeleteModal(false)}
                disabled={loading}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "transparent",
                  color: "var(--text)",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteUser}
                disabled={loading}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--error)",
                  background: "var(--error)",
                  color: "white",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                {loading ? "Deleting..." : "Delete User"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
