#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <ctime>
#include <iomanip>
#include <sstream>
#include <cstdlib>
#include <ctime>
#include <curl/curl.h> // 必须包含 libcurl 头文件

// Windows 特定头文件
#include <windows.h>
#include <conio.h>
#include <io.h>

using namespace std;

const int MAX_TR = 10000;
const int MAX_ST = 1000;

map<string, int> S;
int id;

struct sta {
    int num;
    string name, arr, dep;
};
sta stInfo[MAX_TR][MAX_ST];
string trInfo[MAX_TR][3];
int stNum[MAX_TR];
int sum;
string input;

// --- CURL 辅助函数 ---

// 回调函数：将 CURL 获取的数据写入 string 中，替代文件写入
size_t WriteCallback(char* contents, size_t size, size_t nmemb, void* userp) {
    ((std::string*)userp)->append((char*)contents, size * nmemb);
    return size * nmemb;
}

// 专门用于解析 API 返回的 JSON 辅助函数
void parseApiResponse(const string& data, string& outType, string& outModel) {
    // 模拟原始代码中寻找 ":" 和引号的逻辑
    // 原始逻辑: 寻找 "key":"value" 结构
    int s = 0;
    for (size_t i = 0; i < data.length() && s <= 3; i++) {
        if (data[i] == '\"' && i + 1 < data.length() && data[i + 1] == ':' && data[i + 2] == '\"') {
            s++;
            i += 2; // 跳过 :" 
            continue;
        }
        
        if (s == 1) { // 第一个键值对
            if (data[i] == '\"') s++; 
            else outType += data[i];
        } else if (s == 3) { // 第二个键值对
            if (data[i] == '\"') break; 
            else outModel += data[i];
        }
    }
}
long long transfer(const string& timeStr) {
    struct std::tm tm = {};
    std::istringstream iss(timeStr);
    iss >> std::get_time(&tm, "%Y-%m-%d %H:%M");
    if (iss.fail()) { return -1; }
    tm.tm_isdst = -1;
    std::time_t timestamp = std::mktime(&tm);
    if (timestamp == -1) { return -1; }
    return static_cast<long long>(timestamp);
}
// --- 核心爬虫逻辑优化 ---

// 传入一个复用的 CURL* 句柄
string modelCrawler(CURL* curl, string trainCode) {
    string aCode = "", bCode = "";
    string readBuffer;
    CURLcode res;
    
    // 1. 第一次请求：获取 Code
    // 原始代码逻辑：读取网页，寻找 >.../... 结构
    string url1 = "https://train.hao86.com/" + trainCode + "/";
    
    curl_easy_setopt(curl, CURLOPT_URL, url1.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);
    
    res = curl_easy_perform(curl);
    if (res != CURLE_OK) return "common"; // 网络错误直接返回

    // 模拟原始代码的解析逻辑 (读取第5行左右的内容)
    // 原始代码: getline 5次。这里简化处理：直接在全文搜索特征，或者按行分割
    stringstream ss(readBuffer);
    string line;
    int lineCount = 0;
    string targetLine = "";
    while (getline(ss, line)) {
        lineCount++;
        if (lineCount == 5) { // 原始逻辑是跳过前5行，读取第6行的内容？
            targetLine = line; 
            break;
        }
    }
    // 如果按行解析失败，尝试在全文查找 (增强鲁棒性)
    if (targetLine.empty()) targetLine = readBuffer;

    // 解析 aCode 和 bCode
    // 原始逻辑：找第一个 > 后的内容，直到 /
    int s = 0;
    for (size_t i = 0; i < targetLine.length(); i++) {
        while (targetLine[i] != '>' && s == 0) i++;
        if (targetLine[i] == '>') { s++; continue; }
        if (targetLine[i] == '/') { s++; continue; }

        if (isdigit(targetLine[i]) || isalpha(targetLine[i])) {
            if (s == 1) aCode += targetLine[i];
            else if (s == 2) bCode += targetLine[i];
        } else {
            // 原始代码这里有 break，但考虑到结构可能比较紧密，建议只在遇到明显分隔符时break
            // 这里的逻辑保持原样：遇到非数字字母字符就停止提取
            if (s > 0 && !aCode.empty()) break; 
        }
    }

    if (aCode.empty()) return "common";
    
    string model = "common";
    string aM = "", aT = "", bM = "", bT = "";

    // 2. 第二次请求：获取 aCode 信息
    readBuffer.clear();
    string url2 = "https://api.rail.re/train/" + aCode;
    curl_easy_setopt(curl, CURLOPT_URL, url2.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);
    
    res = curl_easy_perform(curl);
    if (res == CURLE_OK && readBuffer.length() > 5) {
        parseApiResponse(readBuffer, aT, aM);
    }

    // 3. 第三次请求：获取 bCode 信息 (如果存在)
    if (!bCode.empty()) {
        readBuffer.clear();
        string url3 = "https://api.rail.re/train/" + bCode;
        curl_easy_setopt(curl, CURLOPT_URL, url3.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);
        
        res = curl_easy_perform(curl);
        if (res == CURLE_OK && readBuffer.length() > 5) {
            parseApiResponse(readBuffer, bT, bM);
        }
    }

    // 时间比较逻辑
    if (aM.empty() && (!bM.empty())) model = bM;
    else if ((!aM.empty()) && bM.empty()) model = aM;
    else if ((!aM.empty()) && (!bM.empty())) {
        // transfer 函数保持不变，这里需要声明一下
        // 如果 aT < bT, 选 bM
        long long tA = transfer(aT); 
        long long tB = transfer(bT);
        if (tA != -1 && tB != -1) {
            if (tA < tB) model = bM;
            else model = aM;
        } else {
            model = aM; // 解析失败时的保底
        }
    }

    return model;
}

// 时间转换函数 (保持不变)


void read() {
    ifstream fin("train.txt");
    string currSt, trainCode, dptS, arrS, arrT, depT;
    int ord;
    while (true) {
        fin >> currSt >> trainCode >> dptS >> arrS >> arrT >> depT >> ord;
        if (ord == 0) break;
        if (!S[trainCode]) {
            S[trainCode] = ++id;
            trInfo[id][0] = dptS; trInfo[id][1] = arrS; trInfo[id][2] = trainCode;
        }
        int nowId = S[trainCode];
        stNum[nowId]++;
        stInfo[nowId][stNum[nowId]].dep = depT;
        stInfo[nowId][stNum[nowId]].arr = arrT;
        stInfo[nowId][stNum[nowId]].name = currSt;
        stInfo[nowId][stNum[nowId]].num = ord;
        sum++;
    }
    fin.close();
}

bool cmp(sta A, sta B) { return A.num < B.num; }

void process() {
    // 1. 初始化 libcurl 全局环境
    curl_global_init(CURL_GLOBAL_ALL);
    
    // 2. 初始化一个复用的 easy handle
    CURL* curl = curl_easy_init();
    if (!curl) {
        cerr << "Curl initialization failed!" << endl;
        return;
    }
	curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L); // 跳过证书验证
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0L); // 跳过主机名验证
    // 3. 设置通用请求头 (模拟浏览器 + Keep-Alive)
    struct curl_slist* headers = NULL;
    headers = curl_slist_append(headers, "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
    headers = curl_slist_append(headers, "Accept: */*");
    headers = curl_slist_append(headers, "Connection: keep-alive"); // 关键：请求保持连接
    
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L); // 自动跟随重定向
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 15L);       // 超时时间 15秒
    curl_easy_setopt(curl, CURLOPT_TCP_KEEPALIVE, 1L);  // 启用 TCP KeepAlive

    // --- 新增：断点续传检测逻辑 ---
    int start_index = 1; // 默认从1开始
    ifstream prog_in("progress.txt");
    if (prog_in.good()) {
        prog_in >> start_index;
        cout << ">>> From id= " << start_index << " Train <<<" << endl;
    }
    prog_in.close();
    // --------------------------

    ofstream fout;
    
    for (int i = start_index; i <= id; i++) { // 循环起始值修改为 start_index
        if (stNum[i] <= 1) continue;
        if (trInfo[i][0] == trInfo[i][1]) continue;
        
        sort(stInfo[i] + 1, stInfo[i] + stNum[i] + 1, cmp);
        
        string model = modelCrawler(curl, trInfo[i][2]);

        // 优化重试逻辑：只有当结果不合理时才重试
        // 增加最多重试次数限制，防止死循环
        for (int k = 1; k <= 3 && (model == "common"); k++) {
            cout << "Retry " << k << " for " << trInfo[i][2] << endl;
            
            // 退避策略：稍微缩短等待时间，因为现在连接复用更稳定
            // 原始代码 sleep(40000+) 太长，建议缩短
            Sleep(2000 + rand() % 3000); 
            
            // 如果是严重的网络错误，可能需要重置连接
            // curl_easy_reset(curl); // 可选：清空所有设置重新开始
            // 重新设置 header (因为 reset 会清空)
            // 这里不建议 reset，先尝试复用
            
            model = modelCrawler(curl, trInfo[i][2]);
        }

        // --- 新增：三次 Retry 失败后的处理 ---
        if (model == "common") {
            cout << "!!! Progress (" << i << ") Exit !!!" << endl;
            ofstream prog_out("progress.txt");
            prog_out << i; // 记录当前失败的索引
            prog_out.close();
            
            // 清理资源并退出
            curl_slist_free_all(headers);
            curl_easy_cleanup(curl);
            curl_global_cleanup();
            exit(0); // 直接退出程序
        }
        // ----------------------------------

        fout.open("trainP.txt", ios::app);
        fout << trInfo[i][2] << " " << trInfo[i][0] << " " << trInfo[i][1] << " " << stNum[i] << " " << model << endl;
        for (int j = 1; j <= stNum[i]; j++)
            fout << stInfo[i][j].name << " " << stInfo[i][j].num << " " << stInfo[i][j].arr << " " << stInfo[i][j].dep << endl;
        fout.close();

        cout << "Process:" << i << "/" << id << " " << trInfo[i][2] << " " << model << endl;
        
        // 随机延时，保持节奏
        Sleep(500 + rand() % 1000); 
    }

    // 清理工作
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    curl_global_cleanup();
}

int main() {
    srand(GetTickCount());
    read();
    process();
    cout << sum << endl;
    return 0;
}
