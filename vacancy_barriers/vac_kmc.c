/* Rejection-free (Bortz-Kalos-Lebowitz) lattice kMC of chalcogen vacancies on the
 * triangular chalcogen sublattice of an MX2 layer (test B).
 *
 * Process: a vacancy exchanges with a filled neighbour site (6 directions).
 * Barrier: Kang-Weinberg form Ea_eff = Ea + dE/2, floored at max(0, dE), where
 * dE = Eb * (n_after - n_before) and n = number of vacancy neighbours of the moving
 * vacancy (Eb < 0 means vacancies attract and cluster).
 *
 * usage: vac_kmc Ea Eb T L conc t_end max_events seed
 * prints one JSON line: events, simulated time reached, wall time, cluster fraction.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static int L, N;
static unsigned char *occ; /* 1 = vacancy */
static int *vpos;          /* vacancy -> site */
static int *vidx;          /* site -> vacancy index or -1 */
static double *rate;       /* 6 per vacancy */
static double rtab[13];    /* indexed by dn + 6 */
static const int DX[6] = {1, -1, 0, 0, 1, -1}, DY[6] = {0, 0, 1, -1, -1, 1};

static unsigned long long rs;
static double urand(void) {
    rs ^= rs << 13; rs ^= rs >> 7; rs ^= rs << 17;
    return ((rs >> 11) + 0.5) * (1.0 / 9007199254740992.0);
}
static int nb(int s, int d) {
    int x = s % L, y = s / L;
    x = (x + DX[d] + L) % L; y = (y + DY[d] + L) % L;
    return y * L + x;
}
static int nvac(int s, int skip) {
    int n = 0;
    for (int d = 0; d < 6; d++) { int t = nb(s, d); if (t != skip && occ[t]) n++; }
    return n;
}
static void update(int v) {
    int s = vpos[v], nb0 = nvac(s, -1);
    for (int d = 0; d < 6; d++) {
        int t = nb(s, d);
        rate[6 * v + d] = occ[t] ? 0.0 : rtab[nvac(t, s) - nb0 + 6];
    }
}

int main(int argc, char **argv) {
    if (argc < 9) { fprintf(stderr, "usage\n"); return 1; }
    double Ea = atof(argv[1]), Eb = atof(argv[2]), T = atof(argv[3]);
    L = atoi(argv[4]); double conc = atof(argv[5]), t_end = atof(argv[6]);
    long long maxev = atoll(argv[7]); rs = 88172645463325252ULL ^ (unsigned long long)atoll(argv[8]);
    N = L * L;
    int Nv = (int)lround(conc * N); if (Nv < 2) Nv = 2;
    double kT = 8.617333e-5 * T, nu = 1e13;
    for (int dn = -6; dn <= 6; dn++) {
        double dE = Eb * dn, ea = Ea + 0.5 * dE;
        if (ea < dE) ea = dE; if (ea < 0) ea = 0;
        rtab[dn + 6] = nu * exp(-ea / kT);
    }
    occ = calloc(N, 1); vpos = malloc(sizeof(int) * Nv); vidx = malloc(sizeof(int) * N);
    rate = malloc(sizeof(double) * 6 * Nv);
    for (int s = 0; s < N; s++) vidx[s] = -1;
    for (int v = 0; v < Nv;) { int s = (int)(urand() * N); if (!occ[s]) { occ[s] = 1; vpos[v] = s; vidx[s] = v; v++; } }
    for (int v = 0; v < Nv; v++) update(v);

    struct timespec a, b; clock_gettime(CLOCK_MONOTONIC, &a);
    double t = 0; long long ev = 0;
    while (t < t_end && ev < maxev) {
        double R = 0; for (int k = 0; k < 6 * Nv; k++) R += rate[k];
        if (R <= 0) break;
        double x = urand() * R, acc = 0; int k = 0;
        for (; k < 6 * Nv - 1; k++) { acc += rate[k]; if (acc >= x) break; }
        int v = k / 6, d = k % 6, s = vpos[v], tgt = nb(s, d);
        occ[s] = 0; occ[tgt] = 1; vidx[s] = -1; vidx[tgt] = v; vpos[v] = tgt;
        /* local update: vacancies within two hops of s or tgt */
        for (int v2 = 0; v2 < Nv; v2++) {
            int p = vpos[v2], near = (p == tgt);
            for (int d1 = 0; d1 < 6 && !near; d1++) {
                int q = nb(p, d1);
                if (q == s || q == tgt) { near = 1; break; }
                for (int d2 = 0; d2 < 6; d2++) { int r = nb(q, d2); if (r == s || r == tgt) { near = 1; break; } }
            }
            if (near) update(v2);
        }
        t += -log(urand()) / R; ev++;
    }
    clock_gettime(CLOCK_MONOTONIC, &b);
    double wall = (b.tv_sec - a.tv_sec) + 1e-9 * (b.tv_nsec - a.tv_nsec);
    int clus = 0; for (int v = 0; v < Nv; v++) if (nvac(vpos[v], -1) > 0) clus++;
    printf("{\"events\": %lld, \"t_reached_s\": %.6e, \"wall_s\": %.6e, \"n_vac\": %d, "
           "\"sites\": %d, \"cluster_frac\": %.4f}\n", ev, t, wall, Nv, N, (double)clus / Nv);
    return 0;
}
