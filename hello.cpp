
#include<bits/stdc++.h>

using namespace std;
class Person
{
    public:
    int a;
    int b;
    virtual void openmode()=0;
};
class son:public Person
{
    friend ostream &operator<<(ostream cout,const son s);
    protected:
    string name;
    string id;
    public:
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
ostream &operator<<(ostream cout,const son s)
{
    cout<<s.a<<"\n"<<s.b<<"\n"<<s.id<<"\n"<<s.name<<endl;
    cout.clear();
    return cout;
}
int main()
{
    cout<<"hello,world"<<endl;
    test01();
    return 0;
}