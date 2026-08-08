"use client";
import { useEffect, useRef } from "react";
import { BOARD_HEIGHT, BOARD_WIDTH, type BoardSnapshot } from "@board/contracts";

export function BoardCanvas({
  snapshot,
  onPointer
}: {
  snapshot: BoardSnapshot | null;
  onPointer(x: number, y: number, create: boolean): void;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = BOARD_WIDTH * ratio;
    canvas.height = BOARD_HEIGHT * ratio;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, BOARD_WIDTH, BOARD_HEIGHT);
    context.fillStyle = "#f8fafc";
    context.fillRect(0, 0, BOARD_WIDTH, BOARD_HEIGHT);
    context.strokeStyle = "#dbeafe";
    for (let x = 0; x < BOARD_WIDTH; x += 40) {
      context.beginPath();
      context.moveTo(x, 0);
      context.lineTo(x, BOARD_HEIGHT);
      context.stroke();
    }
    for (let y = 0; y < BOARD_HEIGHT; y += 40) {
      context.beginPath();
      context.moveTo(0, y);
      context.lineTo(BOARD_WIDTH, y);
      context.stroke();
    }
    for (const item of snapshot?.items ?? []) {
      context.fillStyle = item.kind === "note" ? "#fef3c7" : "#dbeafe";
      context.fillRect(item.x, item.y, item.width, item.height);
      context.strokeStyle = "#334155";
      context.strokeRect(item.x, item.y, item.width, item.height);
      context.fillStyle = "#0f172a";
      context.font = "24px system-ui";
      context.fillText(item.content.slice(0, 24), item.x + 16, item.y + 38);
    }
  }, [snapshot]);

  function coordinates(event: React.MouseEvent<HTMLCanvasElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: (event.clientX - rect.left) * (BOARD_WIDTH / rect.width),
      y: (event.clientY - rect.top) * (BOARD_HEIGHT / rect.height)
    };
  }

  return <canvas
    ref={canvasRef}
    className="aspect-video w-full touch-none rounded border bg-white"
    aria-label="실시간 협업 보드"
    onPointerMove={(event) => {
      const point = coordinates(event);
      onPointer(point.x, point.y, false);
    }}
    onDoubleClick={(event) => {
      const point = coordinates(event);
      onPointer(point.x, point.y, true);
    }}
  />;
}
