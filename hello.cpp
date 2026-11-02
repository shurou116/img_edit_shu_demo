
#include<bits/stdc++.h>

using namespace std;
class Person
{
    public:
    int a;
    virtual void openmode()=0;
};
class son:public Person
{
    public:
    string name;
    string id;
    void openmode()
    {
        cout<<"this is my-projects"<<endl;
    }
};
void test01()
{
    son s1;
    s1.openmode();
}
int main()
{
    cout<<"hello,world"<<endl;
    test01();
    return 0;
}