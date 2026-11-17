# Paper 2 — Topic, vai trò smart contract và bản đồ chứng minh sau Gate 21

## 1. Khóa lại định hướng

Working title: **Economic Design of Smart-Contract Carbon Pools: Participation,
Value Allocation, and Upstream Transmission in Biochar Supply Chains.**

Blockchain/smart contracts là đối tượng phân tích; biochar carbon-removal supply
chain là bối cảnh kinh tế; ReFi là ứng dụng. Không cần chứng minh một công thức
phí chỉ blockchain mới tính được. Nhưng phải chỉ rõ executable rule nào thay đổi
choice set, net payoff hoặc quyền hưởng giá trị. Không gọi mọi kết quả routing/
revenue sharing chung là blockchain-specific novelty.

Central RQ: **Các quy tắc giao dịch và phân bổ giá trị được lập trình nên được
thiết kế thế nào để cân bằng participation, pool composition và khả năng truyền
lợi ích về upstream production?** Đây là định hướng contribution, chưa phải một
optimal-mechanism theorem tổng quát đã hoàn thành.

Chuẩn hóa ba RQ để manuscript không đổi cách đánh số theo các Gates:

- RQ1: Inventory-dependent fees và execution rules ảnh hưởng participation/routing thế nào?
- RQ2: Designer nên chọn economic rule nào, dưới constraints nào và với trade-offs gì?
- RQ3: Khi nào lợi ích monetization truyền thành producer income và production?

Governance hiện xác định ai có quyền chọn/thay đổi rules; chưa là một RQ equilibrium
độc lập. Gate numbers là lịch sử audit và phát triển, không phải các section paper.

## 2. Smart contract làm gì trong mô hình?

| Thành phần | Vai trò thực sự | Không được tự suy ra |
|---|---|---|
| Project inventory | Là input on-chain cho phí phụ thuộc trạng thái | Mọi environmental record đều đúng hoặc oracle không có lỗi |
| Fee calculator | Tính deposit/redemption fee theo rule và branch | Phí số thực giống hệt EVM hoặc deployed version tại mọi block |
| Pool execution | Kiểm tra cap và điều kiện; mint/burn/transfer theo đường thực thi | Giao dịch giả định luôn vượt qua toàn bộ eligibility/seeding/cap checks |
| Fee allocation | Phân chia token theo recipients/shares được cấu hình | Ví đó thuộc producer hoặc khoản đó là vốn trước sản xuất |
| Administrative rights | Owner có thể sửa scale/recipients và các quyền liên quan | Quyền này đã được phân quyền hoặc commitment bất biến |
| Audit trail | Cho phép đối chiếu rules, states và receipts khi lấy được dữ liệu | Tự chứng minh causal effect lên output/carbon removal |

Trong Gate 21, biến thiết kế a là `depositFeeScale` của source, không phải một
"blockchain benefit parameter" thêm vào payoff. Nó đi vào F_a(z), làm thay đổi
marginal monetization và lựa chọn z,y. Đây là vai trò kinh tế cụ thể của code.

Beta là tỷ lệ hợp đồng thương mại chia incremental cash surplus về producer.
Nó không phải fee-recipient percentage. Nếu actor vừa giao dịch vừa nhận phí,
payoff phải tính self-recapture; baseline hiện tách hai vai trò này.

Một conventional marketplace có thể dùng cùng công thức. Paper hiện nghiên cứu
economic design của smart contracts, không chứng minh công nghệ có tính độc quyền
hoặc superiority. Nếu muốn đóng góp về decentralized governance, phải xây thêm
game về control/commitment; không thể suy từ `onlyOwner` thành decentralization.

## 3. Chuỗi quyết định thống nhất

0. Public inventory và contract state được xác định. Designer chọn scale a và cam
   kết trong một horizon theo giả định mô hình.
1. Producer/intermediary đã có procurement contract b0,beta và credit rights.
2. Producer chọn y với cash constraint; physical production và verification tạo eta*y credits.
3. Intermediary chọn z<=eta*y vào pool và bán phần dư ngoài; so sánh net gain sau gas.
4. Smart contract thực thi fee/token allocation; giả định fixed price cho phép cash realization.
5. Producer nhận phần premium theo hợp đồng thương mại; fee recipients nhận token theo rule riêng.

Vì vậy phải phân biệt ba luồng: physical biochar; information/certification; finance.
Market receipts sau issuance không tự tài trợ một khoản chi phải xảy ra trước production.
Các physical/MRV steps là context và assumptions; paper chưa tối ưu pyrolysis hoặc MRV effort.

## 4. Bản đồ toàn bộ nhóm chứng minh theo RQ

Các kết quả trùng nhau giữa Gates được gộp; không đếm một lemma được kiểm tra lại
thành nhiều contributions. R là real-formula proof; C là conditional economics;
S là synthetic computation; E/D là source/deployed EVM evidence; T là actual transaction.

### RQ1 — Rules -> participation, execution và routing

| ID | Nhóm kết quả | Nội dung dễ hiểu | Nguồn/phạm vi |
|---|---|---|---|
| R1.1 | Participation thresholds | Chỉ giao dịch khi giá trị sau phí/gas tốt hơn outside option | Gates 9,18; R/C; fixed-price baseline |
| R1.2 | Self-recapture | Gross fee không phải net private cost nếu trader cũng là recipient | Gates 9,10,18; C; cần đúng net entitlement |
| R1.3 | maxFee tối ưu | Cap cân bằng success payoff với failure gas; vẫn phải so với abstention | Gates 9,10,18; exogenous fee distribution |
| R1.4 | Cap nonuniqueness | Atoms/gaps có thể làm nhiều caps cùng tối ưu | Gate 18; không khẳng định unique cap |
| R1.5 | HHI accounting | Gross project deposit/redemption làm concentration đổi theo công thức chính xác | Gates 8,9,18; không phải causal response |
| R1.6 | Marginal fee schedules | Trong source real interior, dominant-project deposits đắt hơn và redemptions rẻ hơn | Gates 9,11,18; giữ Q và x cố định khi lấy đạo hàm |
| R1.7 | Boundary jumps | Single-project branch khác giới hạn multi-project | Gates 9–11,18; source-default .99; real và EVM phải tách |
| R1.8 | Quadratic asymptotics | Minority entry fee và gần-boundary redemption có thể nhỏ bậc hai | Gates 10,18; không loại bỏ integer fee guards/dust fallback |
| R1.9 | Dynamic domain | Ratio 1.25 tạo điều kiện x<4Q-5q trong dynamic branch | Gates 16–18; không là universal 80% cap |
| R1.10 | Optimal pooled lot | Với partial allocation, lot được chọn theo marginal fee, không bắt buộc bằng toàn bộ production | Gates 19–20; R/C |

R1.1 ở dạng deposit: P[x-F(x)]-vx-g_s>=0. R1.3 có threshold khi fee distribution
và gas ngoại sinh; distribution/cap-dependent strategic ordering chưa được giải.
R1.10: nếu có interior lot optimum, P-v-P F'(z_star)=0. Do đó fee rule tạo một
giới hạn monetization kinh tế ngay cả khi production và vốn vẫn có thể tăng.

### RQ2 — Economic design của rule

| ID | Nhóm kết quả | Nội dung dễ hiểu | Nguồn/phạm vi |
|---|---|---|---|
| R2.1 | Continuity vs incentives | Smoothing làm phí liên tục chưa chắc giữ monotonic incentives | Gates 10,11,18; real proof |
| R2.2 | Clipping/extension | Có thể xây real-valued rules liên tục và weakly monotone | Gates 11,18; chưa là deployed hoặc optimal rule |
| R2.3 | Fee convexity in lot | Dynamic deposit fee tăng lồi theo lượng giao dịch | Gate 19; fixed q,Q và log domain |
| R2.4 | Self-batch identity | Cùng project, fixed rules, không interleaving: tổng fee ideal không giảm khi chia lô | Gate 20; rounding/thresholds ngoài theorem |
| R2.5 | Finite search existence | Enumerate toàn bộ approved candidates cho optimum trong tập hữu hạn | Gates 11,18,21; không mở rộng thành functional optimum |
| R2.6 | Scale-response ordering | Scale thấp hơn weakly tăng selected production dưới partial model | Gate 21; fixed ratio/beta/prices; smallest-optimum tie convention |
| R2.7 | Exact HHI lot cap | Inventory preference chuyển thành một giới hạn quantity rõ bằng đại số | Gate 21; H_bar>=H_initial, H_bar<1 |
| R2.8 | Composition blocks expansion | Nếu maximum pooled lot được phép nhỏ hơn baseline credit supply thì không thể mở rộng output | Gate 21; source-real response family |
| R2.9 | Lowest feasible menu scale | Lowest feasible scale là weak output optimum trong approved menu | Gate 21; fees themselves không assumed monotone |

Designer hiện tối đa modeled eta*y, với fee-token budget và HHI limit được khai báo.
Đây là normative objective, không phải empirical preference của CHAR owner. Share
weights không được tối ưu trong baseline: nếu recipients không tác động decisions
và beta cố định, đổi weights chỉ redistribute, không tự làm tăng participation.

### RQ3 — Monetization -> income -> production

| ID | Nhóm kết quả | Nội dung dễ hiểu | Nguồn/phạm vi |
|---|---|---|---|
| R3.1 | Fixed-premium optimum | Producer chọn stationary output rồi clip vào zero/cash bound | Gates 12,18; Delta cố định với own y |
| R3.2 | No automatic transmission | Beta=0 giữ nguyên production khi primitives khác cố định | Gates 12–13,18–20; intermediary vẫn có thể pool |
| R3.3 | Conditional fee derivative | Fee giảm có thể tăng output khi premium dương, output interior và cash slack | Gates 12,18; fixed success probability nếu dùng pi |
| R3.4 | Cash barrier | Thu nhập về sau không tự mở rộng cash trước production | Gates 12–13,18–20 |
| R3.5 | Response bound | Output change bị chặn bởi pass-through và cost curvature | Gates 13,18; fixed-premium extension |
| R3.6 | Identification limit | Fee shares/issuance không nhận diện duy nhất commercial beta | Gates 13,18; không có identified set thực nghiệm |
| R3.7 | Endogenous all-output solution | Hai concave branches cho global production/channel choice | Gate 19; không là endogenous-price equilibrium |
| R3.8 | Lower-output counterexample | Có thể higher profit/lower output khi ép toàn bộ lot vào một kênh | Gate 19; đã được Gate 20 giới hạn, không làm main general theorem |
| R3.9 | Global ties | Mỗi branch unique không kéo theo toàn bộ choice unique | Gates 19–20; channel-switch threshold |
| R3.10 | Partial output floor | Được chọn lượng pooling thì y*>=outside output nếu outside terms không đổi | Gate 20; nguyên lý nested choices chung |
| R3.11 | Beta/output ordering | Trong partial model, tăng beta không giảm selected output | Gate 20; giữ b0,L,prices và route choice convention cố định |
| R3.12 | Saturation | Producer có thể nhận premium mà output không tăng dù không thiếu vốn | Gate 20; pooling lot đã đạt mức tối ưu |
| R3.13 | Activation/strict expansion | Cần active pooling, beta>0, baseline cash slack và chưa saturation | Gate 20; ngoài knife-edge tie |
| R3.14 | Frozen premium is no bound | Gas dilution và marginal fee effects làm old approximation có thể lệch hai chiều | Gate 19 |

Redemption-demand response và upstream/downstream trade-off trong Gate 12 là các
conditional comparative statics của buyer và producer riêng; chưa là joint market
equilibrium. Chúng hỗ trợ RQ1/RQ3, không được nâng thành welfare coordination theorem.

## 5. Kết quả nào nên đứng ở main text?

Đề xuất main logic (chưa khóa novelty):

1. Executable fee rules xác định feasible and profitable transaction choices.
2. Intermediary optimal partial pooling tạo đường truyền marginal monetization về producer.
3. Thiết kế scale phải cân bằng output, inventory composition và token-fee budget.
4. Beta, finance và saturation quyết định thu nhập tăng có thành physical expansion hay không.

Taylor expansions, decoder checks, accounting identities, real/EVM discrepancies
và original simulation reproductions thuộc appendix/validation support. Gate 19
negative-output result nên là robustness contrast nếu all-output covenant có nền
tảng thể chế, không được dùng để tạo headline chung.

## 6. Evidence ledger — không lẫn proof với dữ liệu

- R/C: các công thức và kết quả trên đã có derivations với assumptions và domains rõ.
- S: original Gates 9–13 tái lập; 27 regenerated archived CSVs khớp local, 20 summaries
  khớp CI. Các policy improvements vẫn là synthetic; Gate 11 volume intervals bao gồm zero.
- E/D: source EVM và deployed-calculator checkpoint tests đã PASS ở các runs đã nêu.
  Mã nguồn công khai và deployed bytecode chưa được khớp hoàn toàn.
- T: whole-pool transaction reconciliation chưa hoàn tất do extraction failure.
- Attribution: recipient wallets -> producers; beta; realized financing; additional
  physical removal chưa được xác minh.

Smart contract ghi allocation rõ hơn không đồng nghĩa producer được thêm vốn;
token retirement không đồng nghĩa physical additionality mới.

## 7. Paper hiện là phương pháp gì?

Hiện là formal economic rule design + globally solved partial-equilibrium responses
+ computational verification, được neo vào source/deployment audit. Leader chọn a,
producer chọn y, intermediary chọn z; baseline information là public, beta cho trước.
Không có hidden-type reports, revelation principle, screening IC hoặc consensus
game. Vì vậy không gọi các kết quả hiện có là một Bayesian mechanism-design theorem.

Gate 21 làm designer problem rõ hơn nhưng mới globally optimal trong finite menu.
Governance choice, continuous/function-space optimal fees, endogenous token prices
và causal effect chưa hoàn tất. Literature novelty audit vẫn cần đóng trước khi
khẳng định contribution ở mức journal cụ thể.

## 8. Tiêu chí giữ đúng định hướng

Mọi kết quả main phải trả lời: rule/control nào của smart contract là input; actor
thay đổi quyết định gì; điều kiện nào làm kết quả đúng; và đâu là phần có thể kiểm
chứng. Nếu một kết quả chỉ là revenue-sharing/routing chung, dùng nó làm benchmark
hoặc điều kiện giới hạn, không gắn nhãn blockchain-specific một cách tự động.
Phần tiếp theo nên làm mạnh continuous fee design hoặc commitment governance,
chọn một nhánh thay vì thêm đồng thời nhiều uncertainty/private types mới.
