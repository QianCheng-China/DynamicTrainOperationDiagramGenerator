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
char option[1000];
string input;
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
	if(aCode.empty())return "common";string model="";
	//vis[aCode]=1;if(!bCode.empty())vis[bCode]=1;
	
	
	string aM="",aT="",bM="",bT="";
	
	sprintf(option,"curl -s \"https://api.rail.re/train/%s\" > tmp.txt",aCode.c_str());
	system(option);fin.open("tmp.txt",ios::in);getline(fin,input);fin.close();
	for(int i=0,s=0;s<=3&&input.length()>5;i++){
		if(input[i]=='\"'&&input[i+1]==':'&&input[i+2]=='\"'){s++;i+=2;continue;}
		if(s==1){for(;input[i]!='\"';i++)aT+=input[i];s++;}
		else if(s==3){for(;input[i]!='\"';i++)aM+=input[i];break;}
	}
	
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
int main(){
	cout<<modelCrawler("G413");
	
	return 0;
}