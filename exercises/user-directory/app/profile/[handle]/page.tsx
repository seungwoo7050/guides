// [Implementation 6] Resolve the dynamic segment in a server component so direct access and client navigation share one route contract.
export default async function ProfilePage({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  return <main><h1>{handle} profile</h1><p>This value was resolved from the dynamic route segment.</p></main>;
}
