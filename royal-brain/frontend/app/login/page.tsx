import LoginForm from "./LoginForm";

type PageProps = {
  searchParams: Promise<{
    reason?: string;
  }>;
};

export default async function LoginPage({ searchParams }: PageProps) {
  const { reason } = await searchParams;
  return <LoginForm reason={reason} />;
}
