# Normalized AST contract

`parse --json`과 성공한 `check --json`은 구현 내부 pointer나 class 이름이 아닌 normalized AST를 출력합니다. 모든 node는 `kind`, non-negative integer `id`, envelope와 같은 source identity의 UTF-8 byte `span`을 갖습니다. Child span은 parent span 안에 있고 `Module` span은 source 전체입니다.

필수 kind/child field:

| Kind | 필수 field |
|---|---|
| `Module` | `functions` |
| `FunctionDecl` | `name`, `parameters`, `return_type`, `body` |
| `Parameter` | `name`, `type` |
| `BlockStmt` | `statements` |
| `LetStmt`, `VarStmt` | `name`, `type`, `initializer` |
| `AssignStmt` | `target`, `value` |
| `ExprStmt` | `expression` |
| `IfStmt` | `condition`, `then_branch`, `else_branch` |
| `WhileStmt` | `condition`, `body` |
| `ReturnStmt` | `value` |
| `CallExpr` | `callee`, `arguments` |
| `NameExpr` | `name` |
| `IntLiteral`, `BoolLiteral`, `StringLiteral` | `value` |
| `UnaryExpr` | `operator`, `operand` |
| `BinaryExpr` | `operator`, `left`, `right` |
| `ErrorExpr`, `ErrorStmt` | `diagnostic_code` |

성공한 program은 `functions`가 비어 있지 않습니다. `kind/id/span` 중 일부만 넣은 object는 node가 아닌 것으로 우회할 수 없으며 거부됩니다. Golden comparison은 `id`와 `span`을 제거한 projection을 사용하므로 내부 allocation order나 절대 경로를 강제하지 않습니다.
