# JDK·JVM과 첫 프로그램

Java 개발의 첫 최소선은 코드를 많이 아는 것이 아니라 다음 순환을 스스로 돌릴 수 있는 상태입니다.

```text
소스 작성 → 컴파일 → 실행 → 결과와 종료 상태 확인 → 수정
```

이 장에서는 편집기 기능에 기대지 않고 터미널에서 이 순환을 직접 확인합니다.

## 소스, 바이트코드와 실행 환경

Java 소스는 `.java` 파일에 작성합니다. `javac`는 소스를 JVM이 읽을 수 있는 `.class` 바이트코드로 컴파일하고, `java`는 클래스패스에서 진입 클래스를 찾아 JVM에서 실행합니다.

```text
Hello.java --javac--> Hello.class --java/JVM--> 실행 결과
```

JDK에는 `javac`, `java`, `jcmd`, `jstack`, `jfr`와 표준 라이브러리가 포함됩니다. JVM은 바이트코드 실행, 메모리 관리, 스레드와 런타임 서비스를 담당합니다.

이 가이드는 컴파일러와 Maven을 실행하는 JVM을 JDK 21로 고정하고, `--release 17`로 생성할 바이트코드와 사용 가능한 표준 API를 Java 17에 맞춥니다. 실행 JDK와 컴파일 대상 release는 서로 다른 계약입니다.

## 현재 도구 확인

```sh
java -version
javac -version
./mvnw -version
```

세 결과에서 JDK 21이 확인되어야 합니다. `java`와 `javac`는 21인데 Maven 출력의 Java 경로가 다르다면 `JAVA_HOME`과 `PATH`의 순서를 확인합니다.

macOS에서는 설치된 JDK를 다음처럼 찾을 수 있습니다.

```sh
/usr/libexec/java_home -V
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
export PATH="$JAVA_HOME/bin:$PATH"
```

Linux에서는 실제 실행 파일 경로를 기준으로 `JAVA_HOME`을 정할 수 있습니다.

```sh
java_path=$(readlink -f "$(command -v java)")
export JAVA_HOME=${java_path%/bin/java}
export PATH="$JAVA_HOME/bin:$PATH"
```

가이드의 스크립트는 시스템 JDK나 셸 설정을 대신 설치·수정하지 않습니다. `./prepare.sh`는 필요한 명령과 버전을 검사하고 문제가 있으면 변경 없이 중단합니다.

## 첫 소스 작성

저장소 밖의 임시 디렉터리에서 직접 확인해도 되고, [첫 명령행 프로그램 실습](../../exercises/01-language-and-domain/01-first-program/README.md)의 skeleton을 사용해도 됩니다.

```sh
work_dir=$(mktemp -d)
mkdir -p "$work_dir/src/dev/guides/hello"
```

`$work_dir/src/dev/guides/hello/Hello.java`를 작성합니다.

```java
package dev.guides.hello;

public final class Hello {
  private Hello() {}

  public static void main(String[] args) {
    String name = args.length == 0 ? "developer" : args[0];
    System.out.println("안녕하세요, " + name + "님.");
  }
}
```

패키지 이름과 소스 경로를 맞춘 뒤 컴파일 결과를 별도 디렉터리에 둡니다.

```sh
mkdir -p "$work_dir/out"
javac --release 17 \
  -d "$work_dir/out" \
  "$work_dir/src/dev/guides/hello/Hello.java"

java -cp "$work_dir/out" dev.guides.hello.Hello Seungwoo
```

`-d`는 클래스 파일의 출력 루트를 정하고 `-cp`는 실행 시 클래스 탐색 루트를 정합니다. 파일 경로를 `java`에 전달하는 것이 아니라 완전한 클래스 이름을 전달합니다.

## 진입점과 종료 상태

JVM이 일반 애플리케이션을 시작할 때 찾는 진입점은 다음 시그니처입니다.

```java
public static void main(String[] args)
```

명령행 인자는 공백 기준으로 나뉜 문자열 배열입니다. 정상 결과는 표준 출력, 진단은 표준 오류에 기록하고 실패는 0이 아닌 종료 상태로 구분합니다.

```java
public static void main(String[] args) {
  if (args.length == 0) {
    System.err.println("이름이 필요합니다.");
    System.exit(2);
  }
  System.out.println(args[0]);
}
```

셸에서는 종료 상태를 바로 확인할 수 있습니다.

```sh
java -cp "$work_dir/out" dev.guides.hello.Hello
printf 'exit=%s\n' "$?"
```

출력 문구만으로 성공과 실패를 구분하지 않습니다. 자동화 도구는 종료 상태, stdout과 stderr를 각각 계약으로 사용합니다.

## 컴파일 오류, 링크에 가까운 오류와 실행 오류

Java에서 자주 구분할 실패는 다음과 같습니다.

- 문법이나 타입이 맞지 않아 `javac`가 실패합니다.
- 컴파일할 때는 있었던 클래스가 실행 클래스패스에 없어 `ClassNotFoundException`이나 `NoClassDefFoundError`가 납니다.
- 진입 클래스 이름이나 패키지 경로가 맞지 않습니다.
- 프로그램이 실행된 뒤 입력이나 상태 때문에 예외가 발생합니다.

오류 메시지에서는 첫 컴파일 진단이나 마지막 `Caused by`가 가리키는 원인을 먼저 확인합니다. 실행 오류의 스택 추적은 위에서부터 읽으며, 예외가 발생한 지점에 가장 가까운 첫 사용자 코드 프레임과 그 호출 경로를 함께 확인합니다.

## 런타임 정보 관찰

[JVM 실행 환경 확인 예제](../../examples/runtime-model/README.md)를 실행합니다.

```sh
./mvnw -pl :runtime-model package
java -cp examples/runtime-model/target/classes \
  dev.guides.java.runtime.RuntimeProbe
```

Java 버전, 설치 경로, VM 이름, 운영체제, CPU 구조, 문자 인코딩과 시간대는 재현 가능한 버그 보고의 일부입니다. 로컬에서만 실패하는 문제를 공유할 때 비밀값을 제거한 뒤 이 정보를 함께 남깁니다.

## 환경이 엇갈릴 때의 진단 순서

1. `pwd`와 대상 저장소 루트를 확인합니다.
2. `command -v java`, `command -v javac`로 실제 실행 파일을 확인합니다.
3. `java -version`, `javac -version`, `./mvnw -version`을 비교합니다.
4. `JAVA_HOME`이 실제 JDK 루트를 가리키는지 확인합니다.
5. 터미널의 `./verify.sh`가 실패하는지 먼저 확인합니다.
6. 터미널은 성공하고 편집기만 실패하면 프로젝트 모델과 캐시를 다시 불러옵니다.

환경 문제를 해결하기 위해 사용자 홈, 전역 Maven 저장소나 편집기 설정을 무작정 삭제하지 않습니다. 관찰된 차이를 하나씩 제거합니다.

## 완료 기준

다음을 문서 없이 다시 수행할 수 있으면 다음 장으로 넘어갑니다.

- 패키지가 있는 소스를 직접 컴파일하고 실행합니다.
- `.java`, `.class`, JDK와 JVM의 역할을 설명합니다.
- 클래스패스와 완전한 클래스 이름을 구분합니다.
- stdout, stderr와 종료 상태를 따로 확인합니다.
- `java`, `javac`와 Maven이 같은 JDK를 사용하는지 점검합니다.

다음은 [Java 언어 기초](02-java-language-foundations.md)입니다.
