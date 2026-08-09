import websocket from "@fastify/websocket";
import Fastify, { type FastifyRequest } from "fastify";
import { ClientEventSchema } from "./protocol";

type Role = "editor" | "viewer";
type ResolveRole = (request: FastifyRequest) => Role;

export async function buildApp(resolveRole: ResolveRole = () => "editor") {
  const app = Fastify({ logger: false });
  void resolveRole;
  await app.register(websocket);
  app.get("/ws", { websocket: true }, (socket) => {
    socket.on("message", (raw) => {
      const event = ClientEventSchema.safeParse(JSON.parse(raw.toString()));
      // TODO: 구성원 확인, 스냅숏, 브로드캐스트와 잘못된 메시지 처리를 구현해 주세요.
      void event;
    });
  });
  // TODO: 연결 확인 타이머와 `onClose` 정리를 구현해 주세요.
  return app;
}
