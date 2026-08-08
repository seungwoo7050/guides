export default function HomePage() {
  return (
    <>
      <a className="skip-link" href="#main">본문으로 건너뛰기</a>
      <header className="site-header">
        <strong>협업 보드</strong>
      </header>
      <main id="main" className="page" tabIndex={-1}>
        <h1>협업 보드 시작점</h1>
        <p>Runtime과 package 경계를 확인한 뒤 단계 02에서 실제 화면 골격을 확장합니다.</p>
      </main>
    </>
  );
}
