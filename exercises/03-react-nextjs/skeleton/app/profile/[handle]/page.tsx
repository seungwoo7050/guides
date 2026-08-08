export default async function ProfilePage({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  return <main><h1>{handle} 프로필</h1><p>동적 route segment가 전달한 값입니다.</p></main>;
}
