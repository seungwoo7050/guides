// [Implementation 6] 동적 segment는 server component가 해석해 client navigation 없이 직접 접근해도 같은 계약을 제공합니다.
export default async function ProfilePage({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  return <main><h1>{handle} 프로필</h1><p>동적 route segment가 전달한 값입니다.</p></main>;
}
