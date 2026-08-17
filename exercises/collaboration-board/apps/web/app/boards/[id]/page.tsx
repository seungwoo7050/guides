import { BoardCanvas } from "../../../components/BoardCanvas";

export default async function BoardPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <BoardCanvas boardId={id} />;
}
