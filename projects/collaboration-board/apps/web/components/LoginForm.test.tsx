import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { LoginForm } from "./LoginForm";

const login = vi.fn();
vi.mock("../lib/api", () => ({ login: (...args: unknown[]) => login(...args) }));
beforeEach(() => login.mockReset());

it("접근 가능한 로그인 양식을 제출합니다", async () => {
  login.mockResolvedValue({
    id: crypto.randomUUID(),
    handle: "editor",
    displayName: "편집자",
    role: "user",
    status: "active"
  });
  const onLogin = vi.fn();
  render(<LoginForm onLogin={onLogin} />);
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("핸들"), "editor");
  await user.type(screen.getByLabelText("표시 이름"), "편집자");
  await user.click(screen.getByRole("button", { name: "로그인" }));
  expect(login).toHaveBeenCalledWith({ handle: "editor", displayName: "편집자" });
  expect(onLogin).toHaveBeenCalled();
});
