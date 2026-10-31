// 独立 C++ 参考实现，仅用于异构交叉测试，不参与 Python 主程序运行。
// 按所给 PDF 表 D.1 与 D.3 实现；状态用列优先四元素数组表示。
#include <array>
#include <cstdint>
#include <iostream>
#include <iomanip>
#include <string>

using State = std::array<unsigned, 4>;
const unsigned box[16] = {9,4,10,11,13,1,8,5,6,2,0,3,12,14,15,7};

unsigned multiply(unsigned a, unsigned b) {
    unsigned polynomial = 0;
    for (unsigned bit = 0; bit < 4; ++bit)
        if (b & (1u << bit)) polynomial ^= a << bit;
    for (int bit = 6; bit >= 4; --bit)
        if (polynomial & (1u << bit)) polynomial ^= 0x13u << (bit - 4);
    return polynomial;
}

State unpack(unsigned value) {
    return {{(value >> 12) & 15, (value >> 8) & 15, (value >> 4) & 15, value & 15}};
}

unsigned pack(const State& state) {
    return state[0] << 12 | state[1] << 8 | state[2] << 4 | state[3];
}

std::array<unsigned, 3> expand(unsigned key) {
    unsigned words[6] = {key >> 8, key & 255, 0, 0, 0, 0};
    for (unsigned i = 2; i < 6; i += 2) {
        const unsigned last = words[i - 1];
        const unsigned rotatedSub = (box[last & 15] << 4) | box[last >> 4];
        words[i] = words[i - 2] ^ rotatedSub ^ (i == 2 ? 0x80 : 0x30);
        words[i + 1] = words[i] ^ last;
    }
    return {{words[0] << 8 | words[1], words[2] << 8 | words[3], words[4] << 8 | words[5]}};
}

void addKey(State& state, unsigned key) {
    const State other = unpack(key);
    for (unsigned i = 0; i < 4; ++i) state[i] ^= other[i];
}

void substitute(State& state, bool inverse) {
    for (auto& nibble : state) {
        if (inverse) {
            for (unsigned i = 0; i < 16; ++i) if (box[i] == nibble) { nibble = i; break; }
        } else nibble = box[nibble];
    }
}

void shift(State& state) { std::swap(state[1], state[3]); }

void mix(State& state, bool inverse) {
    const State before = state;
    const unsigned a = inverse ? 9 : 1, b = inverse ? 2 : 4;
    for (unsigned column = 0; column < 2; ++column) {
        const unsigned i = column * 2;
        state[i] = multiply(a, before[i]) ^ multiply(b, before[i + 1]);
        state[i + 1] = multiply(b, before[i]) ^ multiply(a, before[i + 1]);
    }
}

unsigned encrypt(unsigned plain, unsigned key) {
    State state = unpack(plain);
    const auto keys = expand(key);
    addKey(state, keys[0]);
    substitute(state, false); shift(state); mix(state, false); addKey(state, keys[1]);
    substitute(state, false); shift(state); addKey(state, keys[2]);
    return pack(state);
}

unsigned decrypt(unsigned cipher, unsigned key) {
    State state = unpack(cipher);
    const auto keys = expand(key);
    addKey(state, keys[2]); shift(state); substitute(state, true);
    addKey(state, keys[1]); mix(state, true); shift(state); substitute(state, true); addKey(state, keys[0]);
    return pack(state);
}

int main() {
    // 每行 P K 任意C；输出 Enc(P,K)、Dec(任意C,K)、Dec(Enc(P,K),K)。
    unsigned plain, key, cipher;
    while (std::cin >> std::hex >> plain >> key >> cipher) {
        const unsigned encrypted = encrypt(plain, key);
        std::cout << std::hex << std::uppercase << std::setfill('0')
                  << std::setw(4) << encrypted << ' ' << std::setw(4) << decrypt(cipher, key)
                  << ' ' << std::setw(4) << decrypt(encrypted, key) << '\n';
    }
}
