#include<bits/stdc++.h>
#include<windows.h>
#include<conio.h>
#include<io.h>
#include <iostream>
#include <string>
#include <ctime>
#include <iomanip>
#include <sstream>
using namespace std;
const int MAX_TR=10000;
const int MAX_ST=1000;
map<string,int> S;int id;
struct sta{int num;string name,arr,dep;};
sta stInfo[MAX_TR][MAX_ST];
string trInfo[MAX_TR][3];
int stNum[MAX_TR];
int sum;
string input;
char option[1000];
long long transfer(const string& timeStr){
    struct std::tm tm = {};
    std::istringstream iss(timeStr);
    iss>>std::get_time(&tm, "%Y-%m-%d %H:%M");
    if (iss.fail()) {return -1;}
    tm.tm_isdst = -1;
    std::time_t timestamp = std::mktime(&tm);
    if (timestamp == -1) {return -1;}
    return static_cast<long long>(timestamp);
}
string modelCrawler(string trainCode){
	string aCode="",bCode="";
	ifstream fin;ofstream fout;
	sprintf(option,"curl -s \"https://train.hao86.com/%s/\" > tmp.txt",trainCode.c_str());
	system(option);fin.open("tmp.txt",ios::in);for(int i=1;i<=5;i++)getline(fin,input);fin.close();
	for(int i=0,s=0;i<=input.length();i++){
		while(input[i]!='>'&&s==0)i++;
		if(input[i]=='>'){s++;continue;}
		if(input[i]=='/'){s++;continue;}
		if(isdigit(input[i])||isalpha(input[i])){
			if(s==1)aCode+=input[i];
			else bCode+=input[i];
		}else break;
	}
	if(aCode.empty())return "common";string model="common";
	//vis[aCode]=1;if(!bCode.empty())vis[bCode]=1;
	
	
	string aM="",aT="",bM="",bT="";
	system("del tmp.txt > nul");
	sprintf(option,"curl -s \"https://api.rail.re/train/%s\" > tmp.txt",aCode.c_str());
	system(option);fin.open("tmp.txt",ios::in);getline(fin,input);fin.close();
	for(int i=0,s=0;s<=3&&input.length()>5;i++){
		if(input[i]=='\"'&&input[i+1]==':'&&input[i+2]=='\"'){s++;i+=2;continue;}
		if(s==1){for(;input[i]!='\"';i++)aT+=input[i];s++;}
		else if(s==3){for(;input[i]!='\"';i++)aM+=input[i];break;}
	}
	system("del tmp.txt > nul");
	if(!bCode.empty()){
		sprintf(option,"curl -s \"https://api.rail.re/train/%s\" > tmp.txt",bCode.c_str());
		system(option);fin.open("tmp.txt",ios::in);getline(fin,input);fin.close();
		for(int i=0,s=0;s<=3&&input.length()>5;i++){
			if(input[i]=='\"'&&input[i+1]==':'&&input[i+2]=='\"'){s++;i+=2;continue;}
			if(s==1){for(;input[i]!='\"';i++)bT+=input[i];s++;}
			else if(s==3){for(;input[i]!='\"';i++)bM+=input[i];break;}
		}
	}
	if(aM.empty()&&(!bM.empty()))model=bM;
	else if((!aM.empty())&&bM.empty())model=aM;
	else if((!aM.empty())&&(!bM.empty())){
		if(transfer(aT)<transfer(bT))model=bM;
		else model=aM;
	}
	
	
	if(model.empty())return "common";
	else return model;
}
void read(){
	ifstream fin;ofstream fout;
	string currSt,trainCode,dptS,arrS,arrT,depT;int ord;
	fin.open("train.txt",ios::in);
	while(true){
		fin>>currSt>>trainCode>>dptS>>arrS>>arrT>>depT>>ord;
		if(ord==0)break;
		if(!S[trainCode]){S[trainCode]=++id;trInfo[id][0]=dptS;trInfo[id][1]=arrS;trInfo[id][2]=trainCode;}
		int nowId=S[trainCode];stNum[nowId]++;
		stInfo[nowId][stNum[nowId]].dep=depT;
		stInfo[nowId][stNum[nowId]].arr=arrT;
		stInfo[nowId][stNum[nowId]].name=currSt;
		stInfo[nowId][stNum[nowId]].num=ord; 
		sum++;
	}
	fin.close();
}
bool cmp(sta A,sta B){return A.num<B.num;}
void process(){
	ifstream fin;ofstream fout;
	for(int i=815;i<=id;i++){
		if(stNum[i]<=1)continue;
		if(trInfo[i][0]==trInfo[i][1])continue;
		sort(stInfo[i]+1,stInfo[i]+stNum[i]+1,cmp);
		string model="common";
		model=modelCrawler(trInfo[i][2]);
		for(int k=1;k<=5&&(isdigit(model[1])||model=="common");k++){
			cout<<"retry"<<k<<endl;
			Sleep(40000+2000*(rand()%10)+k*5000);
			model=modelCrawler(trInfo[i][2]);
		}
		fout.open("trainP.txt",ios::app);
		fout<<trInfo[i][2]<<" "<<trInfo[i][0]<<" "<<trInfo[i][1]<<" "<<stNum[i]<<" "<<model<<endl;
		for(int j=1;j<=stNum[i];j++)fout<<stInfo[i][j].name<<" "<<stInfo[i][j].num<<" "<<stInfo[i][j].arr<<" "<<stInfo[i][j].dep<<endl;
		fout.close();
		cout<<"Process:"<<i<<"/"<<id<<" "<<trInfo[i][2]<<" "<<model<<endl;
		Sleep(20000+1000*(rand()%5));	
	}	
}
int main(){
	srand(GetTickCount());
	read();
	process();
	cout<<sum;
	return 0;
}