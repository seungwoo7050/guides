# React 컴포넌트와 상태

React는 DOM 조작 문법을 줄이는 도구라기보다 **현재 상태에서 어떤 화면이 나와야 하는지 선언하는 모델**입니다. component를 나누는 기준은 파일 크기보다 책임, 상태 소유권과 재사용되는 UI 계약입니다.

## 목표

- component, props와 state의 역할을 구분합니다.
- state를 필요한 가장 가까운 공통 소유자에 둡니다.
- 이전 state에서 다음 state를 안전하게 계산합니다.
- 파생 가능한 값을 중복 state로 저장하지 않습니다.
- server·URL·component 상태의 정본을 구분합니다.

## component는 입력을 받아 UI를 반환합니다

```tsx
type TaskItemProps = {
  task: Task;
  onToggle: (id: string) => void;
};

export function TaskItem({ task, onToggle }: TaskItemProps) {
  return (
    <li>
      <label>
        <input
          type="checkbox"
          checked={task.completed}
          onChange={() => onToggle(task.id)}
        />
        {task.title}
      </label>
    </li>
  );
}
```

props는 호출자가 제공하는 입력입니다. child가 props 객체를 직접 바꾸지 않습니다. 변경이 필요하면 callback으로 의도를 전달하고 소유자가 새 state를 만듭니다.

## state는 render 사이에 보존되는 값입니다

```tsx
const [tasks, setTasks] = useState<Task[]>([]);
```

일반 지역 변수는 render마다 다시 계산됩니다. 사용자 상호작용 뒤에도 보존되어 다음 render에 영향을 주는 값만 state로 둡니다.

다음은 state일 수 있습니다.

- input draft
- 선택된 tab
- modal open 여부
- client가 임시로 만든 optimistic item

다음은 보통 기존 값에서 계산합니다.

```tsx
const openCount = tasks.filter((task) => !task.completed).length;
```

`tasks`와 `openCount`를 각각 state로 두면 업데이트 누락으로 어긋날 수 있습니다.

## 이전 state에서 계산할 때 함수형 갱신

```tsx
setTasks((current) => current.map((task) =>
  task.id === id ? { ...task, completed: !task.completed } : task
));
```

여러 update가 batch되거나 callback이 이전 render의 값을 잡고 있을 수 있으므로, 다음 값이 이전 값에 의존하면 updater function을 사용합니다.

```tsx
setCount(count + 1);
setCount(count + 1); // 같은 render의 count를 사용해 1만 증가할 수 있음

setCount((value) => value + 1);
setCount((value) => value + 1); // 2 증가
```

## state를 직접 변경하지 않습니다

```tsx
// 피합니다.
tasks.push(newTask);
setTasks(tasks);
```

같은 배열 참조를 넘기면 React가 변경을 관찰하지 못하거나 memoization 계약이 깨질 수 있습니다.

```tsx
setTasks((current) => [...current, newTask]);
```

중첩 object는 변경되는 경로마다 새 값을 만듭니다. 무조건 깊은 복사를 하는 것이 아니라 state shape를 단순하게 유지합니다.

## 상태를 출처별로 나눕니다

| 상태 | 정본 | 예시 |
|---|---|---|
| server state | API·DB | board, member, activity |
| URL state | 주소 | 검색어, 선택된 board, pagination |
| realtime state | server connection | presence, cursor, patch sequence |
| component state | component | 입력 draft, menu open |

server state를 여러 component의 독립 `useState`로 복사하면 refresh와 mutation 뒤 값이 달라집니다. 한 data boundary에서 가져오고 필요한 child에 전달하거나 적절한 cache layer를 사용합니다.

## state를 올리는 기준

두 sibling이 같은 값을 읽거나 변경해야 하면 가장 가까운 공통 parent가 소유할 수 있습니다. 그러나 모든 state를 page root로 올리면 작은 input 변경도 전체 tree를 복잡하게 만듭니다.

질문은 다음과 같습니다.

1. 이 값을 실제로 바꾸는 주체는 누구인가?
2. 이 값을 동시에 읽어야 하는 가장 가까운 범위는 어디인가?
3. URL이나 server에 이미 정본이 있는가?
4. state가 아니라 계산 가능한가?

## component 경계

다음 이유가 있을 때 분리합니다.

- 독립된 UI 의미와 접근성 계약이 있습니다.
- 별도 state 수명을 가집니다.
- 여러 위치에서 재사용됩니다.
- test에서 독립적으로 관찰할 위험이 있습니다.
- server/client 경계를 줄일 수 있습니다.

단순히 JSX가 열 줄을 넘었다는 이유만으로 의미 없는 wrapper component를 만들 필요는 없습니다.

## key는 항목 identity입니다

```tsx
{tasks.map((task) => <TaskItem key={task.id} task={task} />)}
```

key는 DOM 최적화 hint만이 아니라 이전 component instance와 새 항목을 대응시키는 identity입니다. 정렬·삽입·삭제되는 목록에서 배열 index를 쓰면 input state와 focus가 다른 항목에 붙을 수 있습니다.

## state reset

다른 자원의 편집 화면으로 바뀔 때 child state를 명시적으로 reset해야 할 수 있습니다. key를 사용해 component identity를 바꾸거나, 자원 id 변경에 맞춘 state 설계를 합니다. effect로 모든 props를 state에 복사하고 동기화하는 방식은 중복 정본을 만듭니다.

## 실패 조건

- props를 직접 변경합니다.
- 계산 가능한 값을 별도 state로 보존합니다.
- 이전 값에 의존하면서 captured state로 갱신합니다.
- server·URL 값을 독립 component state로 복사합니다.
- 배열 index를 identity로 사용합니다.
- 모든 state를 전역 또는 page root에 둡니다.

## 연결 실습

[`React와 Next.js`](../../exercises/03-react-nextjs/README.md)에서 이름 draft, 검색 query와 요청 상태를 분리하고 실제 browser로 확인합니다.

## 완료 기준

- props와 state의 소유권 차이를 설명할 수 있습니다.
- 파생값을 중복 state로 저장하지 않습니다.
- 이전 state에서 새 배열·객체를 계산합니다.
- server·URL·component state의 정본을 구분합니다.
- 목록 key를 안정적인 식별자로 선택합니다.

## 다음 단계

사용자 입력과 반복 목록의 구체적인 계약은 [`React 폼과 목록`](02-react-forms-lists.md)에서 다룹니다.
