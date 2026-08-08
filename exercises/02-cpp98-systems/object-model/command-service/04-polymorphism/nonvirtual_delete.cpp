struct Base { virtual void run() {} ~Base() {} };
struct Derived : Base { ~Derived() {} };
int main(){Base *p=new Derived();delete p;}
