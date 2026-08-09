# 사례

## A. 가상 머신 서비스

사용자가 image, instance size, subnet, firewall, boot disk를 선택합니다. 공급자는 physical host와 hypervisor를 운영합니다. 사용자는 OS patch, runtime, application, backup schedule과 scaling rule을 관리합니다.

## B. 관리형 웹 runtime

사용자는 source 또는 container image와 환경 설정을 제출합니다. 서비스가 runtime instance, health routing와 scale-out을 관리합니다. 사용자는 application, dependency version, data, request timeout과 cost limit를 관리합니다.

## C. Event function

object upload가 function을 호출합니다. 실행 환경은 재사용되거나 폐기될 수 있고 최대 실행 시간이 있습니다. event는 실패 후 재전달될 수 있습니다. 사용자는 handler, output, identity, retry·DLQ와 downstream capacity를 관리합니다.

## D. 협업 문서 제품

고객은 계정을 만들고 organization에 사용자를 초대합니다. 공급자가 application, runtime, database와 deployment를 운영합니다. 고객 관리자는 sharing, role, retention과 integration을 설정합니다.

## E. 사내 virtualization cluster

운영팀이 ticket을 받아 VM을 수동 생성합니다. resource pool은 공유되지만 소비자가 self-service API로 생성·해제할 수 없고 사용량 계측과 자동 elasticity가 없습니다.
